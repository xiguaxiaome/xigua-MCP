import cv2
#测试中，还没实现完

# url = "http://admin:admin@192.168.3.11:8081"
# 程序是执行状态，但是没有打开摄像头
# url = "http://admin:123456@192.168.3.16:8081"
# 正确打开摄像头
# rtsp://10.207.226.97:8554/live
# url = "http://admin:admin@10.207.226.97:8081"
url = "http://admin:1234@192.168.116.35:8081"
# url = "rtsp://10.207.226.97:8554/live"
# 直接返回错误：[rtsp @ 000001ee2b0824c0] method DESCRIBE failed: 401 Unauthorized

# url = "rtsp://admin:123456@192.168.3.16:8554/live"
# [rtsp @ 0000019250a424c0] method DESCRIBE failed: 404 Stream Not Found  手机的摄像头会被打开，然后程序报错

print('start')
cap = cv2.VideoCapture(url)#读取视频流
while(cap.isOpened()):
    ret, frame = cap.read()
    print('success')
    cv2.imshow('frame',frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()