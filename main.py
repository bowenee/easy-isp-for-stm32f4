import serial, serial.tools.list_ports
import sys, os, time, re
from datetime import datetime 
import subprocess

UART_LOG = 1
BAUD_RATE = 115200  # stable
# BAUD_RATE = 230400  # middle
# BAUD_RATE = 460800 # sometimes not stable
# BAUD_RATE = 500000 # sometimes not stable
# BAUD_RATE = 600800 # sometimes not stable

#================= functions: ==================
def send_and_get(data='02 fd', num=300, ms=1000, cmd=1):
    # try:
        # 将16进制字符串转换为字节
        # print(data)
        hex_data = bytes.fromhex(data)

        if(not cmd): # data, need add xor
            xor_data = 0
            for byte in hex_data:
                xor_data = xor_data ^ byte
            hex_data = hex_data + bytes([xor_data])
        # print(hex_data)
        if(UART_LOG > 0 and len(hex_data)<20): print('send:%s===' % hex_data.hex(), end='')

        # 发送数据
        ser.write(hex_data)
        
        ms_i = 0
        for ms_i in range(ms):
            if(ser.in_waiting >= num):
                break
            time.sleep(0.001)
        # 读取回复数据
        reply = ser.read(ser.in_waiting)
        
        # 打印回复数据
        # print(reply)
        if(UART_LOG): print('%d===%s' % (ms_i, reply.hex()))
        return reply
    # except:
    #     # 关闭串口
    #     print('serial error!!')
    #     ser.close()

def enter_boot():
    # time.sleep(1)
    return -1 #todo
    ser.write('{"id":"000004","cmd":"heartbeat","type":"request","message":"open","check_sum":"9a"}'.encode('gb2312'))
    time.sleep(0.5)
    if(ser.in_waiting > 150): 
        reply = ser.read(ser.in_waiting)
        if('cmd' in reply.decode('gb2312')):
            ser.write('{"id":"2","cmd":"version","type":"request","message":"","check_sum":"3c"}'.encode('gb2312'))
            time.sleep(0.2)
            reply = ser.read(ser.in_waiting)
            # 使用正则表达式匹配 firmware 的值
            match = re.search(r'"firmware":"(.*?)"', reply.decode('gb2312'))
            reply = match.group(1)
            print('old version: ', end='')
            print(reply)
            
            ser.write('{"id":"2","cmd":"ota","type":"request","message":"","check_sum":"3c"}'.encode('gb2312'))
            time.sleep(0.2)
            return 0
    else:
        return -1

def init_connection():
    reply = send_and_get('7f', num=1)
    if(reply.hex() == '79' or reply.hex() == '1f'):
        print('init success')
        return 0
    reply = send_and_get('7f', num=1)
    if(reply.hex() == '79' or reply.hex() == '1f'):
        print('init success')
        return 1
    return -1

def find_latest_bin_file(directory):
    # 初始化最新文件和修改时间
    latest_file = None
    latest_mtime = datetime.min 

    # 遍历目录中的所有文件
    for filename in os.listdir(directory):
        if filename.endswith('.bin'):
            filepath = os.path.join(directory, filename)
            # 获取文件的最后修改时间
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            # 检查是否是最新修改的文件
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file = filepath
                
    return latest_file

def erase_pages():
    reply = send_and_get('44 bb', num=1, ms=1000)
    if(reply.hex() == '79'):
        reply = send_and_get('0004 0000 0001 0002 0003 0004', num=1, ms=5000, cmd=0)
        # reply = send_and_get('0005 0000 0001 0002 0003 0004 0005', num=1, ms=5000, cmd=0)
        if(reply.hex() == '79'):
            print('erase 0..4 pages success')
            return 0
        else:
            return -2
    else:
        return -1

#================= main: ==================
# 初始化串口
ports = [port.device for port in serial.tools.list_ports.comports()]
ser = 0
for port in ports:
    try:
        ser = serial.Serial(port, 115200)
        # ser = serial.Serial(port, 1000_000, parity=serial.PARITY_EVEN)
        print(f"connected to {port}")
        if(enter_boot() >= 0):
            ser.close()  # Close the port after connecting
            ser = serial.Serial(port, BAUD_RATE, parity=serial.PARITY_EVEN)
            if(init_connection() >= 0):
                break
        else:
            ser.close()  # Close the port after connecting
            ser = serial.Serial(port, BAUD_RATE, parity=serial.PARITY_EVEN)
            if(init_connection() >= 0):
                break

        print(f"close {port}")
        ser.close()  # Close the port after connecting
    except serial.SerialException:
        print(f"failed to connect to {port}")

# ser = serial.Serial('COM3', 115200, parity=serial.PARITY_EVEN) 

if(ports==[] or ser == 0):
    input("there is no avaliable com !!")
    sys.exit()
else:
    if not ser.is_open:
        input("init com fail")
        sys.exit()

latest_file = find_latest_bin_file('.')
app_len = os.path.getsize(latest_file)
print("file: %s, len = %d" % (latest_file, app_len))

var_time = time.time()
print('erase flash ...')
if(erase_pages() < 0):
    ser.close()
    input('erase fail')
    sys.exit()


app_base_addr = 0x0800_0000
percent = 0
UART_LOG = 0 # close progress log 
with open(latest_file, 'rb') as file:
    # 循环读取文件，每次读取256字节
    while True:
        chunk = file.read(256)  # 读取256字节 
        if not chunk:
            break  # 如果没有更多数据，退出循环
        len_chunk = len(chunk)
        
        if(UART_LOG): print("addr=%08x:"% app_base_addr)

        reply = send_and_get('31 ce', num=1, ms=1000)
        if(reply.hex() != '79'): break
        reply = send_and_get("%08x" % app_base_addr, num=1, ms=1000, cmd=0)
        if(reply.hex() != '79'): break
        reply = send_and_get(("%02x" % (len_chunk-1)) + chunk.hex(), num=1, ms=5000, cmd=0)
        if(reply.hex() != '79'): break

        app_base_addr += len(chunk)
        percent = int((app_base_addr - 0x0800_0000)/app_len*100)
        # print('\rpercent=%d%%' % percent, end='')
        print(f"\rprogress: [{'#' * (percent//2)}{'.' * (50 - percent//2)}] {percent}%", end="")

        # 打印读取的二进制数据
        # print(chunk.hex())
        # break

ser.close()
print("\nend cycle, %0.3f" % (time.time() - var_time))

if(percent==100):
    input("update success!!, repower the device !!")
    sys.exit()
else:
    input("update fail!!")
    sys.exit()
# input()
# subprocess.Popen("reset_target.bat", shell=True)
# while True: pass
    # reply = send_and_get('02 fd', num=300, ms=1000)
