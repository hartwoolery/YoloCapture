import { Detection } from "./DetectionHelpers";

@component
export class YoloCapture extends BaseScriptComponent {
  @input enableCapture: boolean = false;
  @input baseURL: string = "";
  @input dataset: string = "";

  private internetModule: InternetModule = require("LensStudio:InternetModule");
  private motionControllerModule = require('LensStudio:MotionControllerModule');

  private isEditor = global.deviceInfoSystem.isEditor();
  private ImageQuality = CompressionQuality.HighQuality;
  private ImageEncoding = EncodingType.Jpg;

  public isCapturing: boolean = false;
  public captureCount: number = 0;


  onAwake() {
    if (this.enableCapture && !this.isEditor) {
      print("tap on your Spectacles mobile controller to capture a frame");
      let controller = this.motionControllerModule.getController(MotionController.Options.create());
      controller.onTouchEvent.add(this.onTouchEvent.bind(this))
    }

  }

  onTouchEvent(normalizedPosition, touchId, timestampMs, phase) {
    if (phase != MotionController.TouchPhase.Began) {
        return
    }

    this.isCapturing = true;
  }

  capture(imageTex: Texture,  detections: Detection[], callback) {
    this.isCapturing = false;
    if (!this.enableCapture) {
        print("Capture is disabled");
        callback(null);
        return;
    }

    this.captureCount++;

    let labels = ""
    for (let detection of detections) {
      labels += detection.index + " " + detection.bbox.join(" ") + "\n";
    }

    print("Making image request...");
    Base64.encodeTextureAsync(
      imageTex,
      (base64String) => {
        print("Image encode Success!");
        
        this.uploadData(labels, base64String, callback);
      },
      () => {
        print("Image encoding failed!");
      },
      this.ImageQuality,
      this.ImageEncoding
    );
  }

  async uploadData(
    labels: string,
    image64: string,
    callback: (response: string) => void
  ) {
    const reqObj = {
        "dataset": this.dataset,
        "image_b64": image64,
        "label": labels
      };

    const webRequest = new Request(
      this.baseURL + "/upload",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(reqObj),
      }
    );

    let resp = await this.internetModule.fetch(webRequest);
    if (resp.status == 200 || resp.status == 201) {
      let bodyText = await resp.text();
      print("GOT: " + bodyText);
      var bodyJson = JSON.parse(bodyText);
      callback(bodyJson);
    } else {
      print("error code: " + resp.status);
      callback(null);
    }
  }
}
