import flet as ft
import os
import shutil
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import tempfile

def main(page: ft.Page):
    # --- 页面设置 ---
    page.title = "超级PDF拆分器"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20
    
    # 定义一些颜色
    BG_COLOR = "#f0f4f8"
    PRIMARY_COLOR = "#3f51b5"

    # --- 状态变量 ---
    selected_file_path = ft.Ref[str]()
    process_log = ft.Column()
    
    # --- 核心逻辑函数 (从之前的脚本改造) ---
    def get_bookmarks_by_level(bookmarks, level=1, current_level=1):
        result = []
        for item in bookmarks:
            if isinstance(item, list):
                result.extend(get_bookmarks_by_level(item, level, current_level + 1))
            elif current_level == level:
                result.append(item)
        return result

    def add_log(message, color="black"):
        process_log.controls.append(ft.Text(message, color=color, size=12))
        page.update()

    def start_process(e):
        if not selected_file_label.value:
            add_log("❌ 请先选择一个PDF文件！", "red")
            return

        # 获取用户选择的层级 (1, 2, 3)
        split_level = int(level_dropdown.value)
        pdf_path = selected_file_label.data # 真实路径
        
        # 显示进度条
        progress_ring.visible = True
        btn_start.disabled = True
        add_log(f"🚀 开始处理，拆分层级：第 {split_level} 级...", PRIMARY_COLOR)
        page.update()

        try:
            # 1. 创建临时目录来存放拆分后的文件
            with tempfile.TemporaryDirectory() as temp_dir:
                reader = PdfReader(pdf_path)
                total_pages = len(reader.pages)
                
                # 提取书签
                try:
                    bookmarks = get_bookmarks_by_level(reader.outline, level=split_level)
                except Exception:
                    add_log("❌ 读取目录失败，该文件可能没有目录或已加密。", "red")
                    bookmarks = []

                if not bookmarks:
                    add_log(f"⚠️ 未找到第 {split_level} 级目录。", "orange")
                    progress_ring.visible = False
                    btn_start.disabled = False
                    page.update()
                    return

                add_log(f"✨ 找到 {len(bookmarks)} 个章节，正在拆分...", "blue")
                
                # 开始拆分
                for i, bookmark in enumerate(bookmarks):
                    title = bookmark.title
                    start_page = reader.get_destination_page_number(bookmark)

                    if i < len(bookmarks) - 1:
                        next_bookmark = bookmarks[i+1]
                        end_page = reader.get_destination_page_number(next_bookmark) - 1
                    else:
                        end_page = total_pages - 1
                    
                    # 清理文件名
                    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    output_name = f"{i+1:02d} - {safe_title}.pdf"
                    output_path = os.path.join(temp_dir, output_name)
                    
                    # 写入
                    writer = PdfWriter()
                    for p in range(start_page, end_page + 1):
                        writer.add_page(reader.pages[p])
                    with open(output_path, "wb") as f:
                        writer.write(f)
                        
                    add_log(f"✔ 已生成: {output_name}", "green")

                # 2. 打包成 ZIP
                add_log("📦 正在打包成压缩文件...", "blue")
                zip_filename = f"拆分结果_{os.path.basename(pdf_path)}.zip"
                zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            zipf.write(os.path.join(root, file), file)
                
                add_log("🎉 处理完成！请点击下方按钮保存。", "green")
                
                # 启用保存按钮
                save_file_picker.result_name = zip_filename # 预设文件名
                save_file_picker.result_path = zip_path     # 暂存源路径以便读取
                btn_save.visible = True
                btn_save.data = zip_path # 把zip路径绑在按钮上

        except Exception as err:
            add_log(f"❌ 发生错误: {str(err)}", "red")
        
        finally:
            progress_ring.visible = False
            btn_start.disabled = False
            page.update()

    # --- 文件选择器逻辑 ---
    def pick_files_result(e: ft.FilePickerResultEvent):
        if e.files:
            file = e.files[0]
            selected_file_label.value = file.name
            selected_file_label.data = file.path # 存储真实路径
            add_log(f"📂 已选择文件: {file.name}")
        page.update()

    def save_file_result(e: ft.FilePickerResultEvent):
        # 用户选好保存位置后，把生成的zip复制过去
        if e.path and btn_save.data:
            shutil.copy(btn_save.data, e.path)
            add_log(f"✅ 文件已保存到: {e.path}", "green")
            ft.SnackBar(text="保存成功！").open = True
            page.update()

    # --- UI 组件初始化 ---
    pick_file_dialog = ft.FilePicker(on_result=pick_files_result)
    save_file_picker = ft.FilePicker(on_result=save_file_result)
    page.overlay.extend([pick_file_dialog, save_file_picker])

    # 界面布局
    title_text = ft.Text("📚 PDF 智能拆分器", size=28, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR)
    
    # 第一步：选文件
    btn_pick = ft.ElevatedButton(
        "选择 PDF 文件", 
        icon=ft.icons.UPLOAD_FILE, 
        on_click=lambda _: pick_file_dialog.pick_files(allowed_extensions=["pdf"])
    )
    selected_file_label = ft.Text("未选择文件", color="grey")

    # 第二步：选层级
    level_dropdown = ft.Dropdown(
        label="选择拆分层级",
        width=200,
        options=[
            ft.dropdown.Option("1", "按第 1 级目录 (章)"),
            ft.dropdown.Option("2", "按第 2 级目录 (节)"),
            ft.dropdown.Option("3", "按第 3 级目录 (小节)"),
        ],
        value="2", # 默认二级
        prefix_icon=ft.icons.FORMAT_LIST_NUMBERED
    )

    # 第三步：开始
    btn_start = ft.ElevatedButton(
        "开始拆分", 
        icon=ft.icons.PLAY_ARROW, 
        bgcolor=PRIMARY_COLOR, 
        color="white",
        on_click=start_process
    )
    progress_ring = ft.ProgressRing(visible=False)
    
    # 第四步：保存
    btn_save = ft.ElevatedButton(
        "下载/保存结果 (ZIP)", 
        icon=ft.icons.DOWNLOAD, 
        bgcolor="green", 
        color="white",
        visible=False,
        on_click=lambda _: save_file_picker.save_file(file_name=save_file_picker.result_name)
    )

    # --- 组装界面 ---
    page.add(
        ft.Column(
            [
                ft.Container(content=title_text, margin=ft.margin.only(bottom=20)),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text("第一步：选择文件", weight=ft.FontWeight.BOLD),
                        ft.Row([btn_pick, selected_file_label], alignment=ft.MainAxisAlignment.START),
                    ]),
                    padding=15, bgcolor="white", border_radius=10
                ),
                ft.Container(height=10), # 间隔
                
                ft.Container(
                    content=ft.Column([
                        ft.Text("第二步：设置", weight=ft.FontWeight.BOLD),
                        level_dropdown,
                    ]),
                    padding=15, bgcolor="white", border_radius=10
                ),
                ft.Container(height=10),
                
                ft.Row([btn_start, progress_ring], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                
                # 日志区域
                ft.Container(
                    content=ft.Column([
                        ft.Text("运行日志：", size=14, color="grey"),
                        ft.Container(
                            content=process_log,
                            height=200, # 固定高度，内容多了滚动
                            border=ft.border.all(1, "#eeeeee"),
                            border_radius=5,
                            padding=10,
                            bgcolor="#fafafa"
                        )
                    ]),
                    padding=15, bgcolor="white", border_radius=10
                ),
                
                ft.Container(height=10),
                ft.Row([btn_save], alignment=ft.MainAxisAlignment.CENTER)
            ],
            scroll=ft.ScrollMode.AUTO
        )
    )

ft.app(target=main)
