# Reframe — GPU Service (for "AI generate" mode)

This is a small, separate FastAPI app (`app.py`) that does one thing: load
Stable Diffusion's inpainting model onto a GPU and run outpainting jobs sent
to it over HTTP. Run it wherever you have (or can borrow) a GPU. Your main
backend and your laptop never load the model — they just send an image +
mask and get a result back.

Once it's running somewhere, point your main backend at it:

```bash
# in backend/.env, or exported before starting uvicorn
GENERATIVE_REMOTE_URL=https://<wherever-this-is-running>
```

That's the only wiring needed — `generative_outpaint_image()` in
`backend/app/image_processing.py` already checks for this variable and
calls out to it instead of loading the model locally. If the remote call
fails for any reason (service asleep, network blip), it automatically falls
back to the non-blurred mirror extension, so a conversion never just errors
out.

Below are three ways to host this, roughly in order of "fastest to try" to
"most production-ready."

---

## Option A — Google Colab (free, fastest to set up, good for testing)

Best for: trying this out today, or running batches occasionally. Downsides:
Colab free-tier sessions disconnect after a period of inactivity (typically
a few hours) or ~12h max, so the URL changes each time you restart, and it's
not something you'd leave running unattended for a public app.

1. Open [colab.research.google.com](https://colab.research.google.com), new notebook.
2. **Runtime → Change runtime type → T4 GPU** (or better, if you have Colab Pro).
3. Paste this into a cell and run it:

   ```python
   !pip install -q fastapi uvicorn python-multipart pillow diffusers transformers accelerate safetensors pyngrok nest_asyncio
   ```

4. Upload `app.py` from this folder to the Colab session (drag it into the
   Files pane on the left, or `%%writefile app.py` and paste its contents
   into a cell).
5. Get a free ngrok authtoken from [dashboard.ngrok.com](https://dashboard.ngrok.com) (free account,
   takes a minute), then run:

   ```python
   from pyngrok import ngrok
   import nest_asyncio, uvicorn, threading

   ngrok.set_auth_token("YOUR_NGROK_TOKEN")
   public_url = ngrok.connect(8000)
   print("Public URL:", public_url)

   nest_asyncio.apply()
   threading.Thread(target=lambda: uvicorn.run("app:app", host="0.0.0.0", port=8000)).start()
   ```

6. Copy the printed public URL (looks like `https://xxxx.ngrok-free.app`)
   and set it as `GENERATIVE_REMOTE_URL` in your backend's `.env`.
7. Test it: `curl https://xxxx.ngrok-free.app/health` should return
   `{"status": "ok", "cuda_available": true, ...}`.

The model downloads (a few GB) the first time you call `/outpaint`, so the
very first request will be slow — subsequent ones are fast.

**Keeping it alive longer:** Colab disconnects idle runtimes. If you're
doing a batch of conversions, keep the tab open and interact with it every
so often; for anything longer-running, move to Option B.

---

## Option B — Hugging Face Spaces with ZeroGPU (free, more persistent)

Best for: a "leave it running" free setup without renting a server. Hugging
Face's ZeroGPU gives Spaces shared access to real GPUs (H200s), allocated
per-request, at no cost, within fair-use quotas.

1. Create a free account at [huggingface.co](https://huggingface.co).
2. **New Space** → choose the **Gradio** SDK → pick a name → set hardware to
   **ZeroGPU** (shown as free in the hardware picker).
3. In the Space's file editor, create `app.py` with a Gradio wrapper around
   the same logic (Spaces expect a Gradio or Streamlit entrypoint, not a
   bare FastAPI app, when using the ZeroGPU free tier):

   ```python
   import spaces
   import torch
   from diffusers import AutoPipelineForInpainting
   import gradio as gr

   pipe = None

   def get_pipe():
       global pipe
       if pipe is None:
           pipe = AutoPipelineForInpainting.from_pretrained(
               "stabilityai/stable-diffusion-2-inpainting",
               torch_dtype=torch.float16,
           ).to("cuda")
       return pipe

   @spaces.GPU  # grabs a GPU for the duration of this call only
   def outpaint(image, mask, prompt):
       result = get_pipe()(
           prompt=prompt or "extend the background naturally, photorealistic, seamless",
           image=image,
           mask_image=mask,
           num_inference_steps=30,
       ).images[0]
       return result

   demo = gr.Interface(
       fn=outpaint,
       inputs=[gr.Image(type="pil"), gr.Image(type="pil"), gr.Textbox()],
       outputs=gr.Image(type="pil"),
   )
   demo.launch()
   ```

4. Add a `requirements.txt` in the Space with: `diffusers`, `transformers`,
   `accelerate`, `safetensors`, `spaces`.
5. Once it's live, call it from your backend using the `gradio_client`
   library instead of raw `requests` (Gradio Spaces expose a client-friendly
   API):

   ```python
   from gradio_client import Client, file
   client = Client("your-username/your-space-name")
   result_path = client.predict(file(seed_path), file(mask_path), prompt, api_name="/predict")
   ```

   This is a slightly different call shape than the raw HTTP `/outpaint`
   endpoint in `_generative_outpaint_remote()` — if you go this route, swap
   that function's body for the `gradio_client` call above instead of
   `requests.post`.

This is genuinely free and much more "always on" than Colab, but does mean
adapting the client call slightly since Spaces speak Gradio's protocol
rather than a plain REST endpoint.

---

## Option C — Cheap on-demand GPU rental (most reliable, a few cents/run)

Best for: if you outgrow the free tiers or want guaranteed uptime/latency.
None of these are free, but they're inexpensive for occasional use and need
no separate client-protocol adaptation — you deploy `app.py` as-is (it's
already a plain FastAPI app) and get back a normal URL.

- **RunPod Serverless** — pay per second of actual GPU time; scales to zero
  when idle, so you're not paying for a server sitting around. Deploy
  `app.py` + `requirements.txt` as a custom container.
- **Modal** — serverless GPU functions with a monthly free-credit tier;
  Python-native deployment (`modal deploy`), no Dockerfile needed.
- **Replicate** — if you'd rather not manage a server at all, Replicate
  hosts inpainting models behind a simple API you call per-request; you pay
  per generation rather than per second of uptime.

Any of these: point `GENERATIVE_REMOTE_URL` at the URL they give you, same
as Option A.

---

## Testing locally before deploying anywhere

You can sanity-check the service on your own machine first (still uses your
GPU/CPU, but confirms the code runs before you deploy it elsewhere):

```bash
cd gpu-service
pip install -r requirements.txt
uvicorn app:app --port 8000
curl http://localhost:8000/health
```