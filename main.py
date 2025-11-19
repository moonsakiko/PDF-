import flet as ft
from pypdf import PdfReader, PdfWriter
import zipfile
import io
import os

# --- 核心逻辑部分 (复用并改造你的原始脚本) ---
def get_bookmarks_by_level(bookmarks, level=1, current_level=1):
    """递归提取指定层级的书签"""
    result = []
    for item in bookmarks:
        if isinstance(item, list):
            result.extend(get_bookmarks_by_level(item, level, current_level + 1))
        elif current_level == level:
            result.append(item)
    return result

def safe_filename(title):
    """清理非法字符"""
    return "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()

def main(page: ft.Page):
    page.title = "PDF 智能拆分器"
    page.scroll = "adaptive"
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- 状态变量 ---
    selected_files = {}  # 存储文件名和路径/对象
    process_log = ft.Column()
    
    # 内存中暂存 ZIP 数据
    zip_buffer = io.BytesIO()

    # --- UI 组件 ---
    
    # 1. 日志显示区
    log_text = ft.Text("等待操作...", size=14, color=ft.colors.GREY)
    
    def add_log(msg, color=ft.colors.BLACK):
        process_log.controls.append(ft.Text(msg, color=color, selectable=True))
        page.update()

    # 2. 文件选择器 (读取)
    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_files.clear()
            file_names = []
            for f in e.files:
                selected_files[f.name] = f.path
                file_names.append(f.name)
            file_info_text.value = f"已选择: {', '.join(file_names)}"
            btn_start.disabled = False
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # 3. 文件保存器 (保存 ZIP)
    def on_save_result(e: ft.FilePickerResultEvent):
        # 这里的逻辑稍有不同，Flet web/mobile 保存二进制流比较特殊
        # 但在本地打包 APK 环境下，save_file 会返回路径，我们需要自己写入
        pass

    # 注意：Flet 的 save_file 在移动端行为主要是让用户选路径
    # 简化起见，我们处理逻辑放在主流程，保存通过 file_picker.save_file 触发 UI
    # 但为了兼容性最好，我们通过 Event 处理保存逻辑稍微复杂，
    # 这里我们用最简单的逻辑：处理完 -> 启用保存按钮 -> 点击弹出保存对话框 -> 写入文件
    
    save_picker = ft.FilePicker(
        on_result=lambda e: save_zip_to_disk(e.path) if e.path else None
    )
    page.overlay.append(save_picker)

    def save_zip_to_disk(path):
        try:
            with open(path, "wb") as f:
                f.write(zip_buffer.getvalue())
            add_log(f"✅ 文件已成功保存到: {path}", ft.colors.GREEN)
            ft.AlertDialog(title=ft.Text("保存成功！"), on_dismiss=lambda e: None).open = True
        except Exception as e:
            add_log(f"❌ 保存失败: {str(e)}", ft.colors.RED)

    # --- 核心业务逻辑 ---
    def start_processing(e):
        if not selected_files:
            return
        
        process_log.controls.clear()
        add_log("🚀 开始处理...", ft.colors.BLUE)
        btn_start.disabled = True
        btn_save.disabled = True
        progress_ring.visible = True
        page.update()

        target_level = int(dd_level.value)
        
        # 重置 ZIP 缓存
        zip_buffer.seek(0)
        zip_buffer.truncate(0)

        success_count = 0

        try:
            # 创建 ZIP 文件对象
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_out:
                
                for fname, fpath in selected_files.items():
                    add_log(f"\n正在读取: {fname}")
                    try:
                        reader = PdfReader(fpath)
                        bookmarks = get_bookmarks_by_level(reader.outline, level=target_level)
                        
                        if not bookmarks:
                            add_log(f"⚠️ 跳过: 未找到第 {target_level} 级目录", ft.colors.ORANGE)
                            continue

                        base_name = os.path.splitext(fname)[0]
                        total_pages = len(reader.pages)

                        for i, bookmark in enumerate(bookmarks):
                            title = bookmark.title
                            start_page = reader.get_destination_page_number(bookmark)
                            
                            # 计算结束页
                            if i < len(bookmarks) - 1:
                                next_bookmark = bookmarks[i+1]
                                end_page = reader.get_destination_page_number(next_bookmark) - 1
                            else:
                                end_page = total_pages - 1

                            # 清理文件名
                            safe_title = safe_filename(title)
                            pdf_out_name = f"{base_name}/{i+1:02d}-{safe_title}.pdf"

                            # 拆分逻辑
                            writer = PdfWriter()
                            for p in range(start_page, end_page + 1):
                                writer.add_page(reader.pages[p])

                            # 写入内存流
                            pdf_bytes = io.BytesIO()
                            writer.write(pdf_bytes)
                            
                            # 写入 ZIP
                            zip_out.writestr(pdf_out_name, pdf_bytes.getvalue())
                            add_log(f"  ├─ 拆分: {safe_title} (P{start_page+1}-P{end_page+1})")

                        success_count += 1

                    except Exception as ex:
                        add_log(f"❌ 处理文件出错: {str(ex)}", ft.colors.RED)

            if success_count > 0:
                add_log(f"\n🎉 处理完成！生成了结果压缩包。", ft.colors.GREEN)
                btn_save.disabled = False
            else:
                add_log("\n⚠️ 没有文件被成功拆分。", ft.colors.ORANGE)

        except Exception as e:
            add_log(f"❌ 全局错误: {str(e)}", ft.colors.RED)
        
        btn_start.disabled = False
        progress_ring.visible = False
        page.update()


    # --- 界面布局 ---
    
    file_info_text = ft.Text("未选择文件")
    
    btn_pick = ft.ElevatedButton(
        "1. 选择 PDF 文件 (支持多选)", 
        icon=ft.icons.UPLOAD_FILE,
        on_click=lambda _: file_picker.pick_files(allow_multiple=True, allowed_extensions=["pdf"])
    )

    dd_level = ft.Dropdown(
        label="拆分依据 (目录层级)",
        value="2",
        options=[
            ft.dropdown.Option("1", "按第 1 级 (章)"),
            ft.dropdown.Option("2", "按第 2 级 (节)"),
            ft.dropdown.Option("3", "按第 3 级 (小节)"),
        ],
        width=200
    )

    btn_start = ft.ElevatedButton(
        "2. 开始拆分", 
        icon=ft.icons.CUT,
        disabled=True,
        on_click=start_processing,
        style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.BLUE)
    )

    progress_ring = ft.ProgressRing(visible=False)

    btn_save = ft.ElevatedButton(
        "3. 保存结果 (ZIP压缩包)",
        icon=ft.icons.SAVE_ALT,
        disabled=True,
        on_click=lambda _: save_picker.save_file(file_name="split_result.zip"),
        style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.GREEN)
    )

    # 组装页面
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("PDF 按目录批量拆分", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                btn_pick,
                file_info_text,
                ft.Divider(),
                dd_level,
                ft.Row([btn_start, progress_ring]),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Text("运行日志:", weight=ft.FontWeight.BOLD),
                        process_log
                    ], scroll="always"),
                    height=300,
                    bgcolor=ft.colors.GREY_100,
                    border_radius=10,
                    padding=10
                ),
                ft.Divider(),
                btn_save,
                ft.Text("提示：结果将打包为 ZIP 下载，解压即可看到文件夹结构。", size=12, color=ft.colors.GREY)
            ]),
            padding=20
        )
    )

ft.app(target=main)
