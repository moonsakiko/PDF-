import flet as ft
import os
import io
import zipfile
import traceback

# ❌ 千万不要在顶部写 "import pypdf"
# 这会导致如果库没装好，APP 直接白屏闪退

def main(page: ft.Page):
    page.title = "PDF 拆分工具"
    page.scroll = "adaptive"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    # --- UI 状态变量 ---
    selected_files = {} # 存储文件名:路径
    
    # --- 日志组件 ---
    log_view = ft.Column(spacing=5)
    
    def log(msg, color=ft.colors.BLACK):
        """向屏幕输出日志，而不是控制台"""
        log_view.controls.append(ft.Text(f"• {msg}", color=color, size=14, selectable=True))
        page.update()

    # --- 核心功能 (点击按钮才触发引用) ---
    def run_processing(e):
        if not selected_files:
            log("❌ 请先选择 PDF 文件", ft.colors.RED)
            return

        btn_run.disabled = True
        btn_save.disabled = True
        progress.visible = True
        log_view.controls.clear()
        page.update()

        log("🚀 正在初始化 PDF 引擎...", ft.colors.BLUE)

        # ==========================================
        # 🛡️ 防白屏核心：在这里才引用 pypdf
        # ==========================================
        try:
            import pypdf
            log(f"✅ 引擎加载成功 (v{pypdf.__version__})", ft.colors.GREEN)
        except ImportError:
            log("❌ 致命错误：缺少 pypdf 库！", ft.colors.RED)
            log("请检查 build.yml 是否包含 --include-packages pypdf", ft.colors.RED)
            progress.visible = False
            btn_run.disabled = False
            page.update()
            return

        # 开始处理逻辑
        try:
            # 准备内存中的 ZIP 文件
            zip_buffer = io.BytesIO()
            success_count = 0

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                
                target_level = int(dd_level.value)
                
                for fname, fpath in selected_files.items():
                    log(f"📂 读取: {fname}")
                    try:
                        reader = pypdf.PdfReader(fpath)
                        # 递归获取书签
                        def get_bookmarks(outlines, level, curr=1):
                            res = []
                            for item in outlines:
                                if isinstance(item, list):
                                    res.extend(get_bookmarks(item, level, curr + 1))
                                elif curr == level:
                                    res.append(item)
                            return res

                        bookmarks = get_bookmarks(reader.outline, target_level)
                        
                        if not bookmarks:
                            log(f"  ⚠️ 跳过：无第 {target_level} 级目录", ft.colors.ORANGE)
                            continue

                        base_name = os.path.splitext(fname)[0]
                        total_pages = len(reader.pages)

                        for i, bm in enumerate(bookmarks):
                            # 获取标题和页码
                            # pypdf 新版中 title 可能为空
                            title = bm.title if bm.title else f"Part_{i+1}"
                            # 清理文件名非法字符
                            safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
                            
                            start = reader.get_destination_page_number(bm)
                            
                            if i < len(bookmarks) - 1:
                                end = reader.get_destination_page_number(bookmarks[i+1]) - 1
                            else:
                                end = total_pages - 1
                            
                            # 修正页码错误
                            if end < start: end = start

                            # 拆分
                            writer = pypdf.PdfWriter()
                            for p in range(start, end + 1):
                                writer.add_page(reader.pages[p])
                            
                            # 写入内存
                            pdf_bytes = io.BytesIO()
                            writer.write(pdf_bytes)
                            
                            # 加入 ZIP
                            zip_path = f"{base_name}/{i+1:02d}-{safe_title}.pdf"
                            zf.writestr(zip_path, pdf_bytes.getvalue())
                            
                        log(f"  ✅ 拆分成功: {len(bookmarks)} 个部分", ft.colors.GREEN)
                        success_count += 1

                    except Exception as file_err:
                        log(f"  ❌ 文件解析错误: {str(file_err)}", ft.colors.RED)

            if success_count > 0:
                log("\n🎉 所有任务完成！请点击下方保存。", ft.colors.BLUE)
                # 将 ZIP 数据存入全局变量，供保存按钮使用
                btn_save.data = zip_buffer.getvalue()
                btn_save.disabled = False
            else:
                log("\n⚠️ 没有生成任何文件", ft.colors.ORANGE)

        except Exception as e:
            log(f"❌ 全局运行错误: {str(e)}\n{traceback.format_exc()}", ft.colors.RED)

        btn_run.disabled = False
        progress.visible = False
        page.update()

    # --- 文件保存逻辑 ---
    def save_result(e: ft.FilePickerResultEvent):
        if e.path and btn_save.data:
            try:
                with open(e.path, "wb") as f:
                    f.write(btn_save.data)
                log(f"✅ 文件已保存: {e.path}", ft.colors.GREEN)
                # 弹窗提示
                dlg = ft.AlertDialog(title=ft.Text("保存成功！"))
                page.dialog = dlg
                dlg.open = True
                page.update()
            except Exception as err:
                log(f"❌ 保存失败: {str(err)}", ft.colors.RED)

    # --- 界面布局组件 ---
    file_picker = ft.FilePicker(on_result=lambda e: update_files(e))
    save_picker = ft.FilePicker(on_result=save_result)
    page.overlay.extend([file_picker, save_picker])

    def update_files(e):
        if e.files:
            selected_files.clear()
            names = []
            for f in e.files:
                selected_files[f.name] = f.path
                names.append(f.name)
            file_info.value = f"已选: {', '.join(names)}"
            file_info.color = ft.colors.BLACK
            page.update()

    file_info = ft.Text("请选择一个或多个 PDF", color=ft.colors.GREY)
    
    dd_level = ft.Dropdown(
        label="拆分依据",
        value="2",
        options=[
            ft.dropdown.Option("1", "按第 1 级 (章)"),
            ft.dropdown.Option("2", "按第 2 级 (节)"),
            ft.dropdown.Option("3", "按第 3 级 (小节)"),
        ],
        width=200
    )

    btn_run = ft.ElevatedButton(
        "2. 开始拆分", 
        icon=ft.icons.CUT, 
        on_click=run_processing,
        style=ft.ButtonStyle(bgcolor=ft.colors.BLUE, color=ft.colors.WHITE)
    )
    
    progress = ft.ProgressBar(visible=False)
    
    btn_save = ft.ElevatedButton(
        "3. 保存结果 (ZIP)", 
        icon=ft.icons.SAVE_ALT,
        disabled=True,
        on_click=lambda _: save_picker.save_file(file_name="split_result.zip"),
        style=ft.ButtonStyle(bgcolor=ft.colors.GREEN, color=ft.colors.WHITE)
    )

    # 组装
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("PDF 智能拆分器", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.ElevatedButton("1. 选择文件", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files(allow_multiple=True, allowed_extensions=["pdf"])),
                file_info,
                ft.Divider(),
                dd_level,
                btn_run,
                progress,
                ft.Container(
                    content=log_view,
                    height=250,
                    bgcolor=ft.colors.GREY_100,
                    border_radius=8,
                    padding=10,
                    scroll=ft.ScrollMode.ALWAYS
                ),
                btn_save
            ])
        )
    )

ft.app(target=main)
