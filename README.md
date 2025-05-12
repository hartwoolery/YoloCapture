# YoloCapture
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Use ngrok or other local tunneling to use locally, or deploy to a service like Render.com

https://your-tunnel.com/upload 
POST with 
{
"dataset": [string],
"image_b64": [base64 image],
"label": [YoloV7 string]
}

visualize a random image in your dataset
https://your-tunnel.com/dataset/[name]/preview

download zip of your dataset
https://your-tunnel.com/dataset/[name]/download