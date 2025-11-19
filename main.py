import flet as ft
import os
import shutil
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import tempfile

def main(page: ft.Page):
    # --- 页面配置 ---
    page.title = "PDF拆分神器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20
    
    # 这里的 print 会输出到安桌的后台日志，方便调试（虽然你看不到，但能防止报错卡死）
    print("App Starting...") 

    # --- 状态变量 ---
    process_log = ft.Column()
    selected_file_path_ref = ft.Ref[str]() # 专门用来存文件路径

    def add_log(message, color="black"):
        process_log.controls.append(ft.Text(message, color=color, size=12))
        try:
            page.update()
        except:
            pass # 防止更新UI时出错导致崩溃

    def start_process(e):
        print("Start Process Clicked")
        if not selected_file_path_ref.current:
            add_log("❌ 请先选择一个PDF文件！", "red")
            return

        split_level = int(level_dropdown.value)
        pdf_path = selected_file_path_ref.current
        
        progress_ring.visible = True
        btn_start.disabled = True
        page.update()

        try:
            add_log(f"🚀 开始处理: {os.path.basename(pdf_path)}", "blue")
            
            # 使用临时文件夹，这是安卓上最安全的做法
            temp_dir = tempfile.mkdtemp()
            print(f"Temp dir: {temp_dir}")
            
            try:
                reader = PdfReader(pdf_path)
                
                # 递归获取书签
                def get_bookmarks(bookmarks, level, current=1):
                    res = []
                    for item in bookmarks:
                        if isinstance(item, list):
                            res.extend(get_bookmarks(item, level, current + 1))
                        elif current == level:
                            res.append(item)
                    return res

                bookmarks = get_bookmarks(reader.outline, split_level)
                
                if not bookmarks:
                    add_log(f"⚠️ 未找到第 {split_level} 级目录，无法拆分。", "orange")
                    return

                add_log(f"✨ 找到 {len(bookmarks)} 个章节...", "green")
                
                # 拆分逻辑
                total_pages = len(reader.pages)
                for i, bookmark in enumerate(bookmarks):
                    title = bookmark.title
                    start = reader.get_destination_page_number(bookmark)
                    
                    if i < len(bookmarks) - 1:
                        next_bm = bookmarks[i+1]
                        end = reader.get_destination_page_number(next_bm) - 1
                    else:
                        end = total_pages - 1

                    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                    if not safe_title: safe_title = f"Chapter_{i+1}"
                    
                    writer = PdfWriter()
                    for p in range(start, end + 1):
                        writer.add_page(reader.pages[p])
                    
                    out_path = os.path.join(temp_dir, f"{i+1:02d}-{safe_title}.pdf")
                    with open(out_path, "wb") as f:
                        writer.write(f)
                
                # 打包 ZIP
                zip_name = f"拆分结果_{os.path.basename(pdf_path)}.zip"
                zip_full_path = os.path.join(tempfile.gettempdir(), zip_name)
                
                with zipfile.ZipFile(zip_full_path, 'w') as z:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            z.write(os.path.join(root, file), file)
                            
                add_log("🎉 打包完成！请点击下方按钮保存。", "green")
                
                # 绑定保存路径
                btn_save.data = zip_full_path
                save_file_picker.result_name = zip_name
                btn_save.visible = True
                
            except Exception as e:
                add_log(f"❌ 处理出错: {e}", "red")
                print(f"Error details: {e}")
            
        except Exception as outer_e:
            add_log(f"❌ 严重错误: {outer_e}", "red")
            
        finally:
            progress_ring.visible = False
            btn_start.disabled = False
            page.update()

    # --- 文件选择逻辑 ---
    def pick_result(e: ft.FilePickerResultEvent):
        if e.files:
            # 注意：安卓上在这个回调里必须立刻保存路径
            file_obj = e.files[0]
            selected_file_path_ref.current = file_obj.path
            file_label.value = file_obj.name
            add_log(f"📂 已加载: {file_obj.name}")
            page.update()

    def save_result(e: ft.FilePickerResultEvent):
        # Flet 提供了 save_file_picker，它会自动处理安卓的存储权限
        if e.path and btn_save.data:
            try:
                shutil.copy(btn_save.data, e.path)
                add_log(f"✅ 保存成功！", "green")
                page.snack_bar = ft.SnackBar(ft.Text("保存成功！"))
                page.snack_bar.open = True
                page.update()
            except Exception as err:
                add_log(f"保存失败: {err}", "red")

    # --- 界面组件 ---
    pick_dialog = ft.FilePicker(on_result=pick_result)
    save_file_picker = ft.FilePicker(on_result=save_result)
    page.overlay.extend([pick_dialog, save_file_picker])

    file_label = ft.Text("未选择文件", color="grey")
    
    level_dropdown = ft.Dropdown(
        label="拆分层级", width=200, value="2",
        options=[ft.dropdown.Option("1", "第1级 (章)"), ft.dropdown.Option("2", "第2级 (节)")]
    )

    btn_start = ft.ElevatedButton("开始拆分", on_click=start_process, bgcolor="blue", color="white")
    progress_ring = ft.ProgressRing(visible=False)
    
    btn_save = ft.ElevatedButton(
        "保存 ZIP 到手机", 
        icon=ft.icons.DOWNLOAD, 
        bgcolor="green", color="white", 
        visible=False,
        on_click=lambda _: save_file_picker.save_file(file_name=save_file_picker.result_name)
    )

    # 布局
    page.add(
        ft.Text("📚 PDF 拆分神器", size=24, weight="bold"),
        ft.Container(height=20),
        ft.Row([ft.ElevatedButton("选择PDF", on_click=lambda _: pick_dialog.pick_files(allowed_extensions=["pdf"])), file_label]),
        ft.Container(height=10),
        level_dropdown,
        ft.Container(height=20),
        ft.Row([btn_start, progress_ring]),
        ft.Container(height=20),
        ft.Container(
            content=process_log, 
            height=200, bgcolor="#f0f0f0", border_radius=10, padding=10, 
            border=ft.border.all(1, "#cccccc")
        ),
        ft.Container(height=10),
        btn_save
    )

ft.app(target=main)
