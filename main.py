import flet as ft
import os
import shutil
import zipfile
import tempfile
import traceback
import time

def main(page: ft.Page):
    # --- 1. 界面美化配置 ---
    page.title = "PDF拆分神器 (Pro)"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO # 整个页面可滚动

    # --- 2. 日志组件 (支持自动滚动) ---
    log_column = ft.Column(
        scroll=ft.ScrollMode.ALWAYS, # 👈 允许内部滚动
        auto_scroll=True,            # 👈 有新消息自动滚到底部
        spacing=5,
    )
    
    # 把日志框装在一个好看的容器里
    log_container = ft.Container(
        content=log_column,
        height=250,  # 固定高度
        bgcolor="#1e1e1e", # 深色背景，像终端
        border_radius=10,
        padding=15,
        border=ft.border.all(1, "#333333"),
        shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.2, "black"))
    )

    def log(msg, color="white"):
        # 加上时间戳
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_column.controls.append(
            ft.Text(f"[{timestamp}] {msg}", color=color, size=13, font_family="monospace")
        )
        page.update()

    # --- 3. 核心逻辑 ---
    def run_split(e):
        btn_action.disabled = True
        page.update()
        
        log("🚀 初始化引擎...", "cyan")
        
        try:
            import PyPDF2
            
            if not selected_file_path.value:
                log("❌ 错误：请先选择一个 PDF 文件", "red")
                btn_action.disabled = False
                page.update()
                return

            # --- 关键修复步骤：搬运文件 ---
            # 安卓的文件路径很特殊，为了防止 0KB，我们先把文件复制到自己的地盘
            original_path = selected_file_path.value
            safe_temp_dir = tempfile.mkdtemp() # 创建私有工作区
            work_pdf_path = os.path.join(safe_temp_dir, "source.pdf")
            
            log(f"📥 正在导入文件到工作区...", "yellow")
            shutil.copy(original_path, work_pdf_path) # 👈 复制文件
            
            reader = PyPDF2.PdfReader(work_pdf_path)
            
            # 获取拆分层级
            level = int(dd_level.value)
            log(f"📖 正在扫描第 {level} 级目录...", "yellow")

            # 递归获取书签
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
            except Exception:
                bookmarks = []

            if not bookmarks:
                log("⚠️ 未找到目录，无法拆分。", "orange")
                btn_action.disabled = False
                page.update()
                return

            count = len(bookmarks)
            log(f"⚡ 发现 {count} 个章节，开始拆分...", "green")
            
            # 进度条
            pb.visible = True
            pb.value = 0
            page.update()

            total_pages = len(reader.pages)
            
            # 拆分循环
            for i, bm in enumerate(bookmarks):
                # 更新进度条
                pb.value = (i + 1) / count
                
                writer = PyPDF2.PdfWriter()
                start = reader.get_destination_page_number(bm)
                
                if i < count - 1:
                    end = reader.get_destination_page_number(bookmarks[i+1]) - 1
                else:
                    end = total_pages - 1
                
                # 写入页面
                for p in range(start, end + 1):
                    writer.add_page(reader.pages[p])
                
                # 处理文件名
                safe_title = "".join(c for c in bm.title if c.isalnum() or c in " -_")
                if not safe_title: safe_title = f"Chapter_{i+1}"
                out_name = f"{i+1:02d}-{safe_title}.pdf"
                out_path = os.path.join(safe_temp_dir, out_name)
                
                with open(out_path, "wb") as f:
                    writer.write(f)
                
                # ✅ debug：检查生成的文件大小
                f_size = os.path.getsize(out_path)
                if f_size == 0:
                    log(f"⚠️ 警告: {out_name} 生成失败 (0KB)", "red")
                else:
                    log(f"✔ 已生成: {out_name} ({f_size//1024}KB)", "green")

            # 打包 ZIP
            log("📦 正在打包压缩...", "cyan")
            zip_name = f"SplitResult_{int(time.time())}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for root, _, files in os.walk(safe_temp_dir):
                    for f in files:
                        if f != "source.pdf": # 别把源文件打包进去
                            z.write(os.path.join(root, f), f)
            
            # 检查 ZIP 大小
            zip_size = os.path.getsize(zip_path)
            log(f"🎉 处理完成！ZIP大小: {zip_size//1024}KB", "green")
            
            # 激活保存按钮
            btn_save.data = zip_path
            file_picker_save.result_name = zip_name
            btn_save.visible = True
            btn_save.text = f"3. 保存结果 ({zip_size//1024} KB)"
            
        except Exception as err:
            log(f"❌ 发生错误: {str(err)}", "red")
            log(traceback.format_exc(), "red")
        
        finally:
            btn_action.disabled = False
            pb.visible = False
            page.update()

    # --- 4. 文件选择器逻辑 ---
    selected_file_path = ft.Ref[str]()
    
    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file_path.value = e.files[0].path
            # 显示文件名（只显示最后一段，美观）
            filename_text.value = e.files[0].name
            log(f"📂 已选择: {e.files[0].name}", "white")
            page.update()

    def on_save_file(e: ft.FilePickerResultEvent):
        if e.path and btn_save.data:
            try:
                shutil.copy(btn_save.data, e.path)
                log("✅ 保存成功！去看看吧。", "green")
                page.snack_bar = ft.SnackBar(ft.Text("保存成功！"), bgcolor="green")
                page.snack_bar.open = True
                page.update()
            except Exception as err:
                log(f"保存失败: {err}", "red")

    file_picker = ft.FilePicker(on_result=on_file_picked)
    file_picker_save = ft.FilePicker(on_result=on_save_file)
    page.overlay.extend([file_picker, file_picker_save])

    # --- 5. 界面布局组装 ---
    
    # 标题栏
    header = ft.Container(
        content=ft.Row([
            ft.Icon(ft.icons.PICTURE_AS_PDF, size=30, color="blue"),
            ft.Text("PDF 拆分神器 Pro", size=22, weight="bold")
        ]),
        margin=ft.margin.only(bottom=20)
    )

    # 文件选择区
    filename_text = ft.Text("未选择文件...", italic=True, color="grey")
    card_pick = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("第一步：选择源文件", weight="bold"),
                ft.Row([
                    ft.ElevatedButton("浏览文件", icon=ft.icons.FOLDER_OPEN, on_click=lambda _: file_picker.pick_files(allowed_extensions=["pdf"])),
                    ft.Container(content=filename_text, width=180)
                ])
            ]),
            padding=15
        )
    )

    # 设置区
    dd_level = ft.Dropdown(
        label="拆分层级", 
        value="2",
        options=[ft.dropdown.Option("1", "第1级 (章)"), ft.dropdown.Option("2", "第2级 (节)"), ft.dropdown.Option("3", "第3级 (小节)")],
        width=200,
        prefix_icon=ft.icons.LAYERS
    )
    card_setting = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("第二步：拆分设置", weight="bold"),
                dd_level
            ]),
            padding=15
        )
    )

    # 操作区
    pb = ft.ProgressBar(width=300, color="blue", bgcolor="#eeeeee", visible=False)
    btn_action = ft.ElevatedButton(
        "开始拆分", 
        icon=ft.icons.BOLT, 
        bgcolor="blue", 
        color="white", 
        width=300, 
        height=45,
        on_click=run_split
    )
    
    btn_save = ft.ElevatedButton(
        "保存结果 (ZIP)", 
        icon=ft.icons.SAVE_ALT, 
        bgcolor="green", 
        color="white", 
        width=300,
        height=45,
        visible=False,
        on_click=lambda _: file_picker_save.save_file(file_name=file_picker_save.result_name)
    )

    # 组装
    page.add(
        header,
        card_pick,
        ft.Container(height=5),
        card_setting,
        ft.Container(height=20),
        ft.Column([btn_action, pb], horizontal_alignment="center"),
        ft.Container(height=20),
        ft.Text("运行日志：", weight="bold"),
        log_container, # 那个黑色的终端框
        ft.Container(height=10),
        ft.Column([btn_save], horizontal_alignment="center"),
        ft.Container(height=50) # 底部留白
    )

ft.app(target=main)
