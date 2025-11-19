import flet as ft
import os
import io
import zipfile

# --- 防崩关键：把第三方库的引用放在函数内部，或用 try 包裹 ---
# 这样即使库没装好，APP也能打开，并提示错误
try:
    from pypdf import PdfReader, PdfWriter
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_ERROR = f"严重错误：无法加载 pypdf 库。\n原因：{str(e)}\n请检查 build.yml 中的 --include-packages 设置。"
except Exception as e:
    IMPORT_ERROR = f"未知启动错误：{str(e)}"

# --- 辅助函数 ---
def safe_filename(title):
    return "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()

def get_bookmarks_by_level(bookmarks, level=1, current_level=1):
    result = []
    for item in bookmarks:
        if isinstance(item, list):
            result.extend(get_bookmarks_by_level(item, level, current_level + 1))
        elif current_level == level:
            result.append(item)
    return result

def main(page: ft.Page):
    page.title = "PDF 拆分工具"
    page.scroll = "adaptive"
    
    # --- 1. 如果启动时报错，直接显示错误界面，不白屏 ---
    if IMPORT_ERROR:
        page.bgcolor = ft.colors.RED_100
        page.add(
            ft.Column([
                ft.Icon(ft.icons.ERROR_OUTLINE, size=60, color=ft.colors.RED),
                ft.Text("程序启动失败", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.RED),
                ft.Text(IMPORT_ERROR, size=16, selectable=True),
                ft.Text("解决方法：请确保 GitHub Action 的 build 命令中包含 --include-packages pypdf", color=ft.colors.GREY_700)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        page.update()
        return
    # ---------------------------------------------------

    # 正常界面逻辑
    selected_files = {}
    zip_buffer = io.BytesIO()

    log_view = ft.Column()
    
    def add_log(msg, color=ft.colors.BLACK):
        log_view.controls.append(ft.Text(msg, color=color))
        page.update()

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_files.clear()
            names = []
            for f in e.files:
                selected_files[f.name] = f.path
                names.append(f.name)
            file_status.value = f"已选: {len(names)} 个文件"
            btn_run.disabled = False
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    save_picker = ft.FilePicker(
        on_result=lambda e: save_zip(e.path) if e.path else None
    )
    page.overlay.append(save_picker)

    def save_zip(path):
        try:
            with open(path, "wb") as f:
                f.write(zip_buffer.getvalue())
            add_log(f"✅ 保存成功: {path}", ft.colors.GREEN)
        except Exception as e:
            add_log(f"❌ 保存失败: {e}", ft.colors.RED)

    def start_split(e):
        btn_run.disabled = True
        page.update()
        log_view.controls.clear()
        add_log("⏳ 开始处理...", ft.colors.BLUE)
        
        target_level = int(dd_level.value)
        zip_buffer.seek(0)
        zip_buffer.truncate(0)
        
        success_cnt = 0

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname, fpath in selected_files.items():
                    add_log(f"正在读取: {fname}")
                    try:
                        reader = PdfReader(fpath)
                        outlines = reader.outline
                        bookmarks = get_bookmarks_by_level(outlines, level=target_level)
                        
                        if not bookmarks:
                            add_log(f"⚠️ 跳过: 无第 {target_level} 级目录", ft.colors.ORANGE)
                            continue
                            
                        base = os.path.splitext(fname)[0]
                        total_pages = len(reader.pages)
                        
                        for i, bm in enumerate(bookmarks):
                            try:
                                # 处理有些书签没有 title 的情况
                                title = bm.title if bm.title else f"Untitled_{i}"
                                start = reader.get_destination_page_number(bm)
                                
                                if i < len(bookmarks) - 1:
                                    end = reader.get_destination_page_number(bookmarks[i+1]) - 1
                                else:
                                    end = total_pages - 1
                                
                                if end < start: end = start # 防止页码倒挂

                                writer = PdfWriter()
                                for p in range(start, end + 1):
                                    writer.add_page(reader.pages[p])
                                
                                pdf_bytes = io.BytesIO()
                                writer.write(pdf_bytes)
                                
                                clean_title = safe_filename(title)
                                z_name = f"{base}/{i+1:02d}-{clean_title}.pdf"
                                zf.writestr(z_name, pdf_bytes.getvalue())
                                
                            except Exception as inner_e:
                                print(f"书签处理错误: {inner_e}") # 忽略单个书签错误

                        add_log(f"✅ 拆分完成", ft.colors.GREEN)
                        success_cnt += 1
                        
                    except Exception as f_err:
                        add_log(f"❌ 文件错误: {f_err}", ft.colors.RED)

            if success_cnt > 0:
                btn_save.disabled = False
                add_log("🎉全部完成，请点击下方保存按钮", ft.colors.BLUE)
            else:
                add_log("没有文件生成", ft.colors.GREY)

        except Exception as z_err:
            add_log(f"❌ ZIP 打包错误: {z_err}", ft.colors.RED)
        
        btn_run.disabled = False
        page.update()

    # UI 组件
    btn_pick = ft.ElevatedButton("1. 选择文件", icon=ft.icons.UPLOAD, on_click=lambda _: file_picker.pick_files(allow_multiple=True))
    file_status = ft.Text("未选择")
    
    dd_level = ft.Dropdown(
        value="2", 
        label="拆分层级", 
        width=150,
        options=[ft.dropdown.Option("1"), ft.dropdown.Option("2"), ft.dropdown.Option("3")]
    )
    
    btn_run = ft.ElevatedButton("2. 开始拆分", icon=ft.icons.CUT, on_click=start_split, disabled=True)
    btn_save = ft.ElevatedButton("3. 保存结果", icon=ft.icons.SAVE, on_click=lambda _: save_picker.save_file(file_name="result.zip"), disabled=True, bgcolor=ft.colors.GREEN, color=ft.colors.WHITE)

    page.add(
        ft.Text("PDF 目录拆分器 (修复版)", size=20, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        btn_pick,
        file_status,
        ft.Row([ft.Text("目录级别:"), dd_level]),
        btn_run,
        ft.Divider(),
        ft.Container(content=log_view, height=200, bgcolor=ft.colors.GREY_100, padding=10, border_radius=5, overflow=ft.ScrollMode.AUTO),
        btn_save
    )

ft.app(target=main)
