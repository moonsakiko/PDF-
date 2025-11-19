import flet as ft
import os
import shutil
import traceback
import tempfile

# ❌ 绝对不要在最上面 import pypdf，防止开局闪退！

def main(page: ft.Page):
    # 1. 【防白屏核心】参考建议：防止安卓 Activity 意外关闭
    page.window_prevent_close = True
    
    page.title = "PDF工具箱"
    page.scroll = "adaptive"
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- 日志系统 (把错误打印在手机屏幕上) ---
    log_col = ft.Column()
    
    def log(msg, color="black"):
        log_col.controls.append(ft.Text(msg, color=color, size=14, selectable=True))
        page.update()

    # --- 2. 解决安卓路径问题的核心函数 ---
    def get_real_path(original_path, filename):
        """
        安卓的 f.path 可能是缓存路径，pypdf 有时读取有问题。
        我们把它复制到 Python 能完全控制的临时目录中。
        """
        try:
            temp_dir = tempfile.gettempdir()
            safe_name = os.path.basename(filename)
            # 构造一个绝对可写的路径
            new_path = os.path.join(temp_dir, safe_name)
            shutil.copy(original_path, new_path)
            return new_path
        except Exception as e:
            log(f"路径转换失败: {e}", "red")
            return original_path

    # --- 核心处理逻辑 ---
    def start_process(e):
        log_col.controls.clear()
        btn_run.disabled = True
        page.update()
        
        log("🔄 正在初始化...", "blue")

        # 3. 【防白屏核心】延迟加载 pypdf
        try:
            import pypdf
            log(f"✅ 引擎就绪 (v{pypdf.__version__})", "green")
        except ImportError:
            log("❌ 致命错误：未找到 pypdf 库！", "red")
            log("请检查 requirements.txt 是否包含 pypdf", "red")
            btn_run.disabled = False
            page.update()
            return

        # 检查文件
        if not selected_file.value:
            log("❌ 请先选择文件", "red")
            btn_run.disabled = False
            page.update()
            return

        try:
            # 获取真实路径（解决 content:// 问题）
            raw_path = selected_file.data # 这里存的是 f.path
            file_name = selected_file.value
            
            log(f"📂 原始路径: {raw_path}", "grey")
            
            # 关键步骤：复制文件到临时区，确保 pypdf 能读
            real_path = get_real_path(raw_path, file_name)
            log(f"🔄 处理路径: {real_path}", "blue")

            # 开始读取 PDF
            reader = pypdf.PdfReader(real_path)
            count = len(reader.pages)
            
            log(f"✅ 成功读取！共 {count} 页。", "green")
            log("🎉 恭喜！防白屏测试成功！", "purple")
            
            # 这里演示拆分前 2 页（证明功能可用）
            writer = pypdf.PdfWriter()
            if count > 0: writer.add_page(reader.pages[0])
            if count > 1: writer.add_page(reader.pages[1])
            
            out_path = os.path.join(tempfile.gettempdir(), "test_output.pdf")
            writer.write(out_path)
            log(f"✅ 测试生成文件: {out_path}", "green")

        except Exception as err:
            # 捕获所有运行错误，打印堆栈
            log(f"❌ 运行报错: {str(err)}", "red")
            log(traceback.format_exc(), "red")

        btn_run.disabled = False
        page.update()

    # --- UI 界面 ---
    selected_file = ft.Text(value="", visible=False) # 存文件名
    selected_file.data = "" # 存路径
    
    file_info = ft.Text("未选择文件")

    def on_pick(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            selected_file.value = f.name
            selected_file.data = f.path
            file_info.value = f"已选: {f.name}"
            # 打印一下路径让开发者看到
            log(f"收到文件: {f.path}", "grey")
            page.update()

    picker = ft.FilePicker(on_result=on_pick)
    page.overlay.append(picker)

    btn_pick = ft.ElevatedButton("1. 选择 PDF", on_click=lambda _: picker.pick_files(allowed_extensions=["pdf"]))
    btn_run = ft.ElevatedButton("2. 测试运行", on_click=start_process, bgcolor="blue", color="white")

    page.add(
        ft.Text("🛡️ PDF 防白屏终极版", size=24, weight="bold"),
        ft.Divider(),
        btn_pick,
        file_info,
        ft.Divider(),
        btn_run,
        ft.Divider(),
        ft.Container(
            content=log_col,
            bgcolor=ft.colors.GREY_100,
            padding=10,
            border_radius=5,
            height=400,
            scroll="always" # 允许滚动查看长日志
        )
    )

ft.app(target=main)
