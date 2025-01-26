from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
import os
import subprocess
import tempfile
import uuid
import logging
import shutil
from datetime import datetime, timedelta
import platform

app = Flask(__name__, static_folder='../frontend')
CORS(app, resources={r"/api/*": {"origins": [
    "http://127.0.0.1:5500",  # 添加这行，允许 Live Server 的地址
    "http://localhost:5500",   # 添加这行
    "https://ebook-convert-for-me.vercel.app",
    "http://localhost:5001"
]}})

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'txt', 'epub', 'mobi', 'azw3'}

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Calibre 工具路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if platform.system() == 'Windows':
    # Windows 路径，用于本地开发
    CALIBRE_PATH = r'D:\小工具\在线转换\Calibre2\ebook-convert.exe'  # 替换为你的本地路径
else:
    # Linux 路径，用于 PythonAnywhere
    CALIBRE_PATH = '/usr/bin/ebook-convert'

# 检查转换工具是否存在
if not os.path.exists(CALIBRE_PATH):
    logger.warning(f"Calibre 转换工具不存在于 {CALIBRE_PATH}，尝试安装...")
    if platform.system() != 'Windows':
        try:
            # 在 Linux 上尝试安装 Calibre
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'calibre'], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"安装 Calibre 失败: {e}")
            raise

# 存储转换后的文件信息
converted_files = {}

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/convert', methods=['POST'])
def convert_file():
    logger.info("收到转换请求")
    
    if 'file' not in request.files:
        logger.error("请求中没有文件")
        return jsonify({'error': '没有文件'}), 400
        
    file = request.files['file']
    target_format = request.form.get('targetFormat', '').lower()
    
    logger.info(f"文件名: {file.filename}, 目标格式: {target_format}")
    source_format = os.path.splitext(file.filename)[1][1:].lower()
    logger.info(f"源文件格式: {source_format}")
    
    if source_format == target_format:
        logger.error("源文件格式和目标格式相同")
        return jsonify({'error': '源文件格式和目标格式相同'}), 400
    
    if file.filename == '':
        logger.error("没有选择文件")
        return jsonify({'error': '没有选择文件'}), 400
        
    if not allowed_file(file.filename):
        logger.error(f"不支持的文件格式: {file.filename}")
        return jsonify({'error': '不支持的文件格式'}), 400
    
    if not target_format:
        logger.error("未指定目标格式")
        return jsonify({'error': '未指定目标格式'}), 400

    # 创建临时工作目录
    work_dir = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()))
    os.makedirs(work_dir, exist_ok=True)
    
    input_path = os.path.join(work_dir, file.filename)
    logger.info(f"准备处理文件: {input_path}")

    try:
        # 保存上传的文件
        file.save(input_path)
        file_size = os.path.getsize(input_path)
        logger.info(f"文件已保存到临时目录，大小: {file_size} 字节")
        
        if not os.path.exists(input_path):
            logger.error("文件保存失败")
            return jsonify({'error': '文件保存失败'}), 500

        # 准备输出文件路径
        output_filename = os.path.splitext(file.filename)[0]
        output_path = os.path.join(work_dir, f"{output_filename}.{target_format}")
        
        logger.info(f"开始转换: {input_path} -> {output_path}")
        
        # 调用 Calibre 转换工具
        command = [CALIBRE_PATH, input_path, output_path]
        logger.info(f"执行命令: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True  # 这会在命令失败时抛出异常
        )

        logger.info(f"转换完成，返回码: {result.returncode}")
        logger.info(f"标准输出: {result.stdout}")
        logger.info(f"标准错误: {result.stderr}")

        if not os.path.exists(output_path):
            logger.error("转换后的文件未找到")
            return jsonify({'error': '转换后的文件未找到'}), 500

        output_size = os.path.getsize(output_path)
        logger.info(f"转换后文件大小: {output_size} 字节")
        
        if output_size == 0:
            logger.error("转换后的文件大小为0")
            return jsonify({'error': '转换失败：输出文件为空'}), 500

        # 生成文件ID并保存信息
        file_id = str(uuid.uuid4())
        converted_name = f"{output_filename}.{target_format}"
        converted_files[file_id] = {
            'path': output_path,
            'original_name': file.filename,
            'converted_name': converted_name,
            'created_at': datetime.now(),
            'work_dir': work_dir
        }

        logger.info(f"转换成功，文件ID: {file_id}")
        logger.info(f"转换后的文件名: {converted_name}")
        
        return jsonify({
            'fileId': file_id,
            'originalName': file.filename,
            'convertedName': converted_name
        })

    except subprocess.CalledProcessError as e:
        logger.exception(f"转换进程错误: {e.stderr}")
        return jsonify({'error': f"转换失败: {e.stderr}"}), 500
    except Exception as e:
        logger.exception("转换过程发生错误")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'error' in locals():
            try:
                shutil.rmtree(work_dir)
            except Exception as cleanup_error:
                logger.error(f"清理临时文件失败: {cleanup_error}")

@app.route('/api/download/<file_id>')
def download_file(file_id):
    logger.info(f"收到下载请求: {file_id}")
    
    if file_id not in converted_files:
        logger.error(f"文件不存在: {file_id}")
        return jsonify({'error': '文件不存在或已过期'}), 404
        
    file_info = converted_files[file_id]
    logger.info(f"找到文件信息: {file_info}")
    
    try:
        if not os.path.exists(file_info['path']):
            logger.error(f"文件不存在于磁盘: {file_info['path']}")
            return jsonify({'error': '文件不存在'}), 404
            
        logger.info(f"开始发送文件: {file_info['path']}")

        # 直接返回文件，不处理 MIME 类型
        return send_file(
            file_info['path'],
            as_attachment=True,
            download_name=file_info['converted_name']
        )
        
    except Exception as e:
        logger.exception("下载文件时发生错误")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) 