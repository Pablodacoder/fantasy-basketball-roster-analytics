import time

class PageLoadTimeMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    start_time = time.time()

    request.start_time = start_time
    response = self.get_response(request)

    duration = round((time.time() - start_time) * 1000, 2)

    if "text/html" in response.get("Content-Type", ""):
      # Decode content, replace placeholder, and re-encode
      content = response.content.decode("utf-8")
      
      # Look for placeholder and replace with the duration
      placeholder = "<!-- PAGE_LOAD_TIME_PLACEHOLDER -->"
      if placeholder in content:
        content = content.replace(placeholder, f"{duration} ms")
        response.content = content.encode("utf-8")
        # Adjust content length header to prevent clipping
        response["Content-Length"] = str(len(response.content))

    # request.page_load_time = duration
    response["X-Page-Generation-Duration-ms"] = duration

    print(f"Page {request.path} load time: {duration} ms")
    
    return response