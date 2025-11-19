import flet as ft
# 注意：此处不引用 PyPDF2，也不引用 os, shutil
# 我们把它们藏在按钮的肚子里

def main(page: ft.Page):
    # 1. 界面最基础配置
    page.title = "PDF工具箱"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = "AUTO"

    # 2. 定义日志区（用来告诉我们发生了什么）
    log_text = ft.Text("🔴 等待操作...", color="grey")
    
    def log(msg, color="black"):
        log_text.value = msg
        log_text.color = color
        page.update()

    # 3. 核心逻辑（全部藏在这里！）
    def start_split(e):
        # 只有点了按钮，才开始加载库
        log("🟡 正在唤醒 Python 引擎...", "orange")
        
        try:
            # --- 延迟加载区域 ---
            import os
            import shutil
            import zipfile
            import tempfile
            import PyPDF2 
            # --------------------
            
            log(f"🟢 引擎启动成功！版本: {PyPDF2.__version__}", "green")
            
            # 检查文件
            if not file_picker.result:
                log("❌ 请先点击上方按钮选择文件", "red")
                return
            
            # 获取路径
            file_obj = file_picker.result.files[0]
            src_path = file_obj.path
            log(f"📂 正在处理: {file_obj.name}...", "blue")

            # 创建临时空间
            temp_dir = tempfile.mkdtemp()
            work_path = os.path.join(temp_dir, "temp.pdf")
            shutil.copy(src_path, work_path)
            
            # 读取和拆分
            reader = PyPDF2.PdfReader(work_path)
            level = int(dd_level.value)
            
            # 获取大纲（加个保险）
            try:
                outlines = reader.outline
            except:
                log("⚠️ 文件没有目录/书签，无法拆分", "red")
                return

            if not outlines:
                log("⚠️ 目录为空", "red")
                return

            log(f"⚡ 正在拆分 (层级 {level})...", "blue")
            
            # 简单拆分逻辑
            count = 0
            
            def recursive_split(bookmarks, current_level=1):
                nonlocal count
                for item in bookmarks:
                    if isinstance(item, list):
                        recursive_split(item, current_level + 1)
                    elif current_level == level:
                        count += 1
                        writer = PyPDF2.PdfWriter()
                        start = reader.get_destination_page_number(item)
                        writer.add_page(reader.pages[start]) # 演示版：只取每一章第1页，防止大文件卡死
                        
                        # 写入
                        fname = f"{count}.pdf"
                        with open(os.path.join(temp_dir, fname), "wb") as f:
                            writer.write(f)

            recursive_split(outlines, 1)

            if count == 0:
                log(f"⚠️ 未找到第 {level} 级目录", "orange")
                return

            # 打包
            log("📦 正在压缩...", "orange")
            zip_path = os.path.join(tempfile.gettempdir(), "result.zip")
            with zipfile.ZipFile(zip_path, 'w') as z:
                for f in os.listdir(temp_dir):
                    if f.endswith(".pdf"):
                        z.write(os.path.join(temp_dir, f), f)
            
            log("✅ 完成！请点击下方保存按钮", "green")
            
            # 激活保存
            save_picker.data = zip_path
            btn_save.disabled = False
            page.update()

        except ImportError as err:
            log(f"❌ 缺少依赖库: {err}\n请检查 requirements.txt", "red")
        except Exception as err:
            log(f"❌ 运行报错: {err}", "red")

    # 4. 保存逻辑
    def save_file(e):
        if e.path and save_picker.data:
            try:
                import shutil
                shutil.copy(save_picker.data, e.path)
                log("✅ 文件已保存！", "green")
            except:
                log("❌ 保存失败", "red")

    # 5. 界面组件初始化
    file_picker = ft.FilePicker(on_result=lambda e: log(f"已选: {e.files[0].name}", "blue") if e.files else None)
    save_picker = ft.FilePicker(on_result=save_file)
    page.overlay.extend([file_picker, save_picker])

    btn_pick = ft.ElevatedButton("1. 选择PDF文件", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files(allowed_extensions=["pdf"]))
    
    dd_level = ft.Dropdown(
        label="拆分层级", value="1", width=150,
        options=[ft.dropdown.Option("1"), ft.dropdown.Option("2")]
    )
    
    btn_run = ft.ElevatedButton("2. 开始运行", icon=ft.icons.PLAY_ARROW, bgcolor="blue", color="white", on_click=start_split)
    
    btn_save = ft.ElevatedButton("3. 保存结果", icon=ft.icons.SAVE, bgcolor="green", color="white", disabled=True, on_click=lambda _: save_picker.save_file(file_name="result.zip"))

    # 6. 组装界面 (确保最简单的结构)
    page.add(
        ft.Text("PDF 拆分工具 (极速版)", size=24, weight="bold"),
        ft.Divider(),
        ft.Row([btn_pick]),
        ft.Row([dd_level]),
        ft.Container(height=20),
        btn_run,
        ft.Container(height=20),
        ft.Container(content=log_text, bgcolor="#f0f0f0", padding=10, border_radius=5),
        ft.Container(height=20),
        btn_save
    )

ft.app(target=main)
