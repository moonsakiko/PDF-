import flet as ft
import traceback # 专门用来抓取错误的工具

# ❌ 严禁在最外层 import 任何其他库
# ❌ 严禁在这里写 os, shutil, PyPDF2

def main(page: ft.Page):
    # 1. 无论如何，先显示一个基本的界面
    page.title = "启动调试模式"
    page.scroll = "ALWAYS"
    
    # 这是一个显示日志的框
    log_view = ft.Column()
    page.add(
        ft.Text("=== 系统启动日志 ===", size=20, weight="bold"),
        ft.Container(
            content=log_view,
            bgcolor="#f0f0f0",
            padding=10,
            border_radius=5
        )
    )
    page.update()

    # 定义一个写日志的函数
    def log(msg, color="black"):
        log_view.controls.append(ft.Text(msg, color=color, fontFamily="monospace"))
        page.update()

    log("✅ UI 壳子启动成功！")
    log("⏳ 正在尝试加载 Python 核心库...")

    # 2. 在这里尝试加载库，如果白屏，错误会显示在这里
    try:
        import os
        import shutil
        import zipfile
        import tempfile
        import time
        
        log("✅ 基础库 (os, shutil...) 加载成功")
        
        try:
            import PyPDF2
            log(f"✅ PyPDF2 加载成功！版本: {PyPDF2.__version__}", "green")
        except ImportError:
            log("❌ 致命错误：找不到 PyPDF2 库！\n请检查 requirements.txt", "red")
            return # 停止运行
            
    except Exception as e:
        log(f"❌ 环境严重错误: {e}", "red")
        log(traceback.format_exc(), "red")
        return

    # 3. 定义核心功能（嵌套在 main 里面）
    def run_split_process(e):
        log("--- 开始任务 ---")
        try:
            if not file_picker.result:
                log("❌ 没选文件", "red")
                return
                
            # 获取文件路径（处理 Flet 在安卓上的特殊路径对象）
            file_obj = file_picker.result.files[0]
            src_path = file_obj.path
            log(f"📂 选中文件: {file_obj.name}")

            # 只有点击按钮时才创建临时目录，避免启动卡死
            temp_dir = tempfile.mkdtemp()
            work_path = os.path.join(temp_dir, "source.pdf")
            
            log("📋 正在复制文件到私有目录...")
            shutil.copy(src_path, work_path)
            
            log("📖 正在读取 PDF...")
            reader = PyPDF2.PdfReader(work_path)
            
            # 简化的拆分逻辑（不再递归，只拆第一级，求稳）
            log("✂️ 开始拆分 (简单模式)...")
            
            # 尝试获取目录
            try:
                outlines = reader.outline
            except:
                log("⚠️ 无法读取目录/书签", "orange")
                return

            if not outlines:
                log("⚠️ 目录为空", "orange")
                return

            # 简单的遍历
            count = 0
            for item in outlines:
                if isinstance(item, list): continue # 跳过复杂子目录
                
                count += 1
                title = item.title
                log(f"   -> 处理章节: {title}")
                
                start = reader.get_destination_page_number(item)
                writer = PyPDF2.PdfWriter()
                writer.add_page(reader.pages[start]) # 为了测试，只存该章节第一页
                
                # 写入
                safe_name = f"{count}.pdf"
                with open(os.path.join(temp_dir, safe_name), "wb") as f:
                    writer.write(f)

            # 打包
            log("📦 正在打包 ZIP...")
            zip_path = os.path.join(tempfile.gettempdir(), "result.zip")
            with zipfile.ZipFile(zip_path, 'w') as z:
                for f in os.listdir(temp_dir):
                    if f.endswith(".pdf"):
                        z.write(os.path.join(temp_dir, f), f)
            
            log("🎉 成功！准备保存...", "green")
            save_picker.save_file(file_name="result.zip")
            
            # 这一步要把 result.zip 路径传给保存器，我们用个全局变量或者闭包
            save_picker.data = zip_path 

        except Exception as err:
            log(f"❌ 运行时错误: {err}", "red")
            log(traceback.format_exc(), "red")

    # 4. 文件保存回调
    def on_save(e):
        try:
            if e.path and save_picker.data:
                shutil.copy(save_picker.data, e.path)
                log(f"✅ 保存成功: {e.path}", "green")
        except Exception as err:
            log(f"保存失败: {err}", "red")

    # 5. 简单的界面元素
    file_picker = ft.FilePicker(on_result=lambda e: log(f"已选: {e.files[0].name}") if e.files else None)
    save_picker = ft.FilePicker(on_result=on_save)
    page.overlay.extend([file_picker, save_picker])

    btn_pick = ft.ElevatedButton("1. 选文件", on_click=lambda _: file_picker.pick_files(allowed_extensions=["pdf"]))
    btn_run = ft.ElevatedButton("2. 运行测试", on_click=run_split_process, bgcolor="blue", color="white")
    
    page.add(
        ft.Divider(),
        btn_pick,
        btn_run,
        ft.Text("如果能看到这个界面，说明没有白屏！", color="grey")
    )

ft.app(target=main)
