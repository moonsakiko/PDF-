import flet as ft
import os
import shutil
import zipfile
import tempfile
import traceback

# ❌ 注意：这里千万不要写 import PyPDF2
# 我们要等界面出来了再引用它，防止开局就崩

def main(page: ft.Page):
    page.title = "PDF拆分神器"
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    # --- 日志显示区 ---
    log_column = ft.Column()
    
    def log(msg, color="black"):
        log_column.controls.append(ft.Text(msg, color=color, size=14))
        page.update()

    # --- 核心功能 (点击按钮才加载) ---
    def run_split(e):
        btn_action.disabled = True
        page.update()
        
        log("🔄 正在尝试加载 PDF 引擎...", "blue")
        
        try:
            # ✅ 关键：在这里引用库！
            # 如果 requirements.txt 没配好，这里会捕获错误并在屏幕显示
            import PyPDF2
            log("✅ 引擎加载成功！版本: " + PyPDF2.__version__, "green")
            
            if not selected_file_path.value:
                log("❌ 请先选择文件", "red")
                btn_action.disabled = False
                page.update()
                return

            # --- 开始干活 ---
            pdf_path = selected_file_path.value
            log(f"📂 正在读取文件: {os.path.basename(pdf_path)}", "blue")
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            reader = PyPDF2.PdfReader(pdf_path)
            
            # 简单的按层级拆分逻辑
            level = int(dd_level.value)
            
            def get_bookmarks(bookmarks, target_level, curr_level=1):
                res = []
                for item in bookmarks:
                    if isinstance(item, list):
                        res.extend(get_bookmarks(item, target_level, curr_level + 1))
                    elif curr_level == target_level:
                        res.append(item)
                return res

            try:
                bookmarks = get_bookmarks(reader.outline, level)
            except:
                bookmarks = []

            if not bookmarks:
                log("⚠️ 没找到目录/书签，无法拆分", "orange")
                btn_action.disabled = False
                page.update()
                return

            log(f"⚡ 找到 {len(bookmarks)} 个章节，正在拆分...", "blue")

            # 拆分循环
            total_pages = len(reader.pages)
            for i, bm in enumerate(bookmarks):
                writer = PyPDF2.PdfWriter()
                start = reader.get_destination_page_number(bm)
                
                if i < len(bookmarks) - 1:
                    end = reader.get_destination_page_number(bookmarks[i+1]) - 1
                else:
                    end = total_pages - 1
                
                for p in range(start, end + 1):
                    writer.add_page(reader.pages[p])
                
                # 清理文件名
                safe_title = "".join(c for c in bm.title if c.isalnum() or c in " -_")
                out_name = f"{i+1:02d}-{safe_title}.pdf"
                with open(os.path.join(temp_dir, out_name), "wb") as f:
                    writer.write(f)

            # 打包 ZIP
            log("📦 正在压缩...", "blue")
            zip_name = f"Result_{os.path.basename(pdf_path)}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_name)
            
            with zipfile.ZipFile(zip_path, 'w') as z:
                for root, _, files in os.walk(temp_dir):
                    for f in files:
                        z.write(os.path.join(root, f), f)
            
            log("🎉 成功！点击下方按钮下载", "green")
            
            # 显示保存按钮
            btn_save.data = zip_path
            btn_save.visible = True
            file_picker_save.result_name = zip_name
            
        except ImportError:
            log("❌ 致命错误：缺少 PyPDF2 库！\n请检查 requirements.txt 是否写对。", "red")
        except Exception as err:
            log(f"❌ 运行出错: {err}", "red")
            # 打印详细错误给开发者看
            print(traceback.format_exc())
        
        finally:
            btn_action.disabled = False
            page.update()

    # --- 界面组件 ---
    selected_file_path = ft.Ref[str]()
    
    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file_path.value = e.files[0].path
            txt_filename.value = e.files[0].name
            log(f"已选择: {e.files[0].name}")
            page.update()

    def on_save_file(e: ft.FilePickerResultEvent):
        if e.path and btn_save.data:
            try:
                shutil.copy(btn_save.data, e.path)
                log("✅ 文件已保存到手机！", "green")
            except Exception as err:
                log(f"保存失败: {err}", "red")

    file_picker = ft.FilePicker(on_result=on_file_picked)
    file_picker_save = ft.FilePicker(on_result=on_save_file)
    page.overlay.extend([file_picker, file_picker_save])

    txt_filename = ft.Text("未选择文件")
    dd_level = ft.Dropdown(
        label="拆分层级", width=150, value="2",
        options=[ft.dropdown.Option("1"), ft.dropdown.Option("2"), ft.dropdown.Option("3")]
    )
    
    btn_pick = ft.ElevatedButton("1. 选择PDF", on_click=lambda _: file_picker.pick_files(allowed_extensions=["pdf"]))
    btn_action = ft.ElevatedButton("2. 开始拆分", on_click=run_split, bgcolor="blue", color="white")
    btn_save = ft.ElevatedButton("3. 保存结果", visible=False, bgcolor="green", color="white",
                                 on_click=lambda _: file_picker_save.save_file(file_name=file_picker_save.result_name))

    # --- 组装界面 ---
    page.add(
        ft.Text("📱 PDF 拆分神器 (安全版)", size=20, weight="bold"),
        ft.Divider(),
        ft.Row([btn_pick, txt_filename]),
        dd_level,
        ft.Container(height=10),
        btn_action,
        ft.Container(height=10),
        ft.Container(content=log_column, height=200, bgcolor="#f0f0f0", border_radius=10, padding=10),
        btn_save
    )

ft.app(target=main)
