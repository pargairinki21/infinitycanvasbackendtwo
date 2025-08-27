from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import os
import platform
from datetime import datetime

# Platform-specific imports
if platform.system() == "Windows":
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        import pythoncom
        import screen_brightness_control as sbc
        WINDOWS_LIBS_AVAILABLE = True
    except ImportError:
        AudioUtilities = None
        IAudioEndpointVolume = None
        CLSCTX_ALL = None
        pythoncom = None
        sbc = None
        WINDOWS_LIBS_AVAILABLE = False
else:
    AudioUtilities = None
    IAudioEndpointVolume = None
    CLSCTX_ALL = None
    pythoncom = None
    sbc = None
    WINDOWS_LIBS_AVAILABLE = False

app = FastAPI(title="Device Control API")

# CORS setup: allow React frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",   # Your frontend
        "http://127.0.0.1:8000",   # Your frontend
        "http://localhost:5173",    # Vite default
        "http://127.0.0.1:5173",   # Vite default
        "http://localhost:3000",    # React default
        "http://127.0.0.1:3000",   # React default
        "http://localhost:8080",    # New origin
        "http://127.0.0.1:8080",   # New origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Save path for camera - store in captured_images folder
# 🔴 Save path for camera - store in captured_images folder
SAVE_PATH = "captured_images/captured_image.jpg"

# 🔊️ VOLUME FUNCTIONS
def get_volume_interface():
    if not WINDOWS_LIBS_AVAILABLE:
        raise Exception("Volume control not available on this platform")
    pythoncom.CoInitialize()
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)

@app.get("/")
def root():
    available_endpoints = ["/take_picture"]
    if WINDOWS_LIBS_AVAILABLE:
        available_endpoints.extend(["/volume/up", "/volume/down", "/volume/mute", "/volume/unmute", "/brightness/up", "/brightness/down"])
    
    return {
        "message": "Device Control API is running", 
        "platform": platform.system(),
        "windows_features_available": WINDOWS_LIBS_AVAILABLE,
        "endpoints": available_endpoints
    }

@app.post("/volume/up")
def volume_up():
    """Increase system volume by 10%"""
    try:
        volume = get_volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
        return {"message": f"Volume increased to {min(current + 0.1, 1.0):.2f}"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/volume/down")
def volume_down():
    """Decrease system volume by 10%"""
    try:
        volume = get_volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)
        return {"message": f"Volume decreased to {max(current - 0.1, 0.0):.2f}"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/volume/mute")
def mute():
    """Mute system volume"""
    try:
        volume = get_volume_interface()
        volume.SetMute(1, None)
        return {"message": "Volume muted"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/volume/unmute")
def unmute():
    """Unmute system volume"""
    try:
        volume = get_volume_interface()
        volume.SetMute(0, None)
        return {"message": "Volume unmuted"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 💡 BRIGHTNESS FUNCTIONS
@app.post("/brightness/up")
def brightness_up():
    """Increase screen brightness by 10%"""
    try:
        if not WINDOWS_LIBS_AVAILABLE:
            return JSONResponse(content={"error": "Brightness control not available on this platform"}, status_code=501)
        current = sbc.get_brightness(display=0)[0]
        new_brightness = min(current + 10, 100)
        sbc.set_brightness(new_brightness, display=0)
        return {"message": f"Brightness increased to {new_brightness}%"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/brightness/down")
def brightness_down():
    """Decrease screen brightness by 10%"""
    try:
        if not WINDOWS_LIBS_AVAILABLE:
            return JSONResponse(content={"error": "Brightness control not available on this platform"}, status_code=501)
        current = sbc.get_brightness(display=0)[0]
        new_brightness = max(current - 10, 0)
        sbc.set_brightness(new_brightness, display=0)
        return {"message": f"Brightness decreased to {new_brightness}%"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 📷 CAMERA FUNCTION
@app.post("/take_picture")
def take_picture():
    """Capture an image from the default camera"""
    try:
        camera = cv2.VideoCapture(0)  # Open the default camera

        if not camera.isOpened():
            return JSONResponse(content={"error": "Camera not accessible"}, status_code=500)

        ret, frame = camera.read()
        if not ret:
            camera.release()
            return JSONResponse(content={"error": "Failed to capture image"}, status_code=500)

        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_images/captured_image_{timestamp}.jpg"
        
        # Save image with timestamp
        cv2.imwrite(filename, frame)
        camera.release()  # Always release camera

        return {"message": "Picture taken successfully", "file": filename}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)