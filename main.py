import flet as ft
import os
import shutil
import zipfile
import tempfile
import traceback # 用于捕获详细错误

# ⚠️ 关键修改：不在开头 import PyPDF2，防止启动崩溃
# from PyPDF2 import PdfReader, PdfWriter (删掉这一行)

def main(page: ft.Page):
    page.title = "PDF拆分神器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    print("App UI Starting...") # 这行虽然你看不到，但在后台是有用的

    # --- 状态变量 ---
    process_log = ft.Column()
    selected_file_path_ref = ft.Ref[str]()

    def add_log(message, color="black"):
        process_log.controls.append(ft.Text(message, color=color, size=12))
        page.update()

    def start_process(e):
        if not selected_file_path_ref.current:
            add_log("❌ 请先选择一个PDF文件！", "red")
            return

        # ⚠️ 关键修改：在这里引用库！这叫“懒加载”
        # 这样如果库有问题，只会报错，不会导致App打不开
        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            add_log("❌ 致命错误：找不到 PyPDF2 库！请检查打包配置 requirements.txt", "red")
            return

        split_level = int(level_dropdown.value)
        pdf_path = selected_file_path_ref.current
        
        progress_ring.visible = True
        btn_start.disabled = True
        page.update()

        try:
            add_log(f"🚀 开始处理: {os.path.basename(pdf_path)}", "blue")
            
            # 创建临时文件夹
            temp_dir = tempfile.mkdtemp()
            
            try:
                reader = PdfReader(pdf_path)
                
                # 递归找书签
                def get_bookmarks(bookmarks, level, current=1):
                    res = []
                    for item in bookmarks:
                        if isinstance(item, list):
                            res.extend(get_bookmarks(item, level, current + 1))
                        elif current == level:
                            res.append(item)
                    return res

                try:
                    bookmarks = get_bookmarks(reader.outline, split_level)
                except Exception:
                    # 有些PDF可能没有outline属性
                    bookmarks = []
                
                if not bookmarks:
                    add_log(f"⚠️ 未找到第 {split_level} 级目录，无法拆分。", "orange")
                    return

                add_log(f"✨ 找到 {len(bookmarks)} 个章节...", "green")
                
                # 拆分核心
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
                zip_name = f"Result_{int(os.path.getsize(pdf_path))}.zip" # 使用大小做随机名防止重名
                zip_full_path = os.path.join(tempfile.gettempdir(), zip_name)
                
                with zipfile.ZipFile(zip_full_path, 'w') as z:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            z.write(os.path.join(root, file), file)
                            
                add_log("🎉 打包完成！请点击下方按钮保存。", "green")
                
                # 准备保存
                btn_save.data = zip_full_path
                save_file_picker.result_name = f"拆分结果_{os.path.basename(pdf_path)}.zip"
                btn_save.visible = True
                
            except Exception as e:
                # 打印详细错误堆栈
                error_msg = traceback.format_exc()
                add_log(f"❌ 处理逻辑出错:\n{error_msg}", "red")
            
        except Exception as outer_e:
            add_log(f"❌ 系统错误: {str(outer_e)}", "red")
            
        finally:
            progress_ring.visible = False
            btn_start.disabled = False
            page.update()

    # --- 文件选择器 ---
    def pick_result(e: ft.FilePickerResultEvent):
        if e.files:
            file_obj = e.files[0]
            selected_file_path_ref.current = file_obj.path
            file_label.value = file_obj.name
            add_log(f"📂 已加载: {file_obj.name}")
            page.update()

    def save_result(e: ft.FilePickerResultEvent):
        # 用户选好位置后保存
        if e.path and btn_save.data:
            try:
                shutil.copy(btn_save.data, e.path)
                add_log(f"✅ 保存成功！", "green")
                page.snack_bar = ft.SnackBar(ft.Text("保存成功！"))
                page.snack_bar.open = True
                page.update()
            except Exception as err:
                add_log(f"保存失败: {err}", "red")

    # --- UI 组件 ---
    pick_dialog = ft.FilePicker(on_result=pick_result)
    save_file_picker = ft.FilePicker(on_result=save_result)
    page.overlay.extend([pick_dialog, save_file_picker])

    file_label = ft.Text("请选择文件...", color="grey")
    
    level_dropdown = ft.Dropdown(
        label="拆分层级", width=200, value="2",
        options=[
            ft.dropdown.Option("1", "第1级 (章)"), 
            ft.dropdown.Option("2", "第2级 (节)"),
            ft.dropdown.Option("3", "第3级 (小节)")
        ]
    )

    btn_start = ft.ElevatedButton("开始拆分", icon=ft.icons.PLAY_ARROW, on_click=start_process, bgcolor="blue", color="white")
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
        ft.Column([
            ft.Text("📄 PDF 智能拆分", size=24, weight="bold"),
            ft.Container(height=10),
            ft.Container(
                content=ft.Row([
                    ft.ElevatedButton("选择PDF", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: pick_dialog.pick_files(allowed_extensions=["pdf"])), 
                    ft.Container(content=file_label, width=150) # 限制宽度防止溢出
                ]),
                bgcolor="#f0f0f0", padding=10, border_radius=10
            ),
            ft.Container(height=10),
            level_dropdown,
            ft.Container(height=20),
            ft.Row([btn_start, progress_ring]),
            ft.Container(height=10),
            ft.Text("运行日志:", size=12, color="grey"),
            ft.Container(
                content=ft.Column([process_log], scroll=ft.ScrollMode.ALWAYS), 
                height=200, bgcolor="#FAFAFA", border=ft.border.all(1, "#eeeeee"), border_radius=5, padding=5
            ),
            ft.Container(height=10),
            btn_save
        ], scroll=ft.ScrollMode.AUTO)
    )

ft.app(target=main)
