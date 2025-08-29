import auth from "@react-native-firebase/auth";
import { API_BASE } from "@/shared/constants/config";

type RequestOptions = {
  headers?: Record<string, string>;
  idempotencyKey?: string;
};

class ApiClient {
  private async request(
    method: string,
    path: string,
    body?: any,
    opts: RequestOptions = {}
  ): Promise<any> {
    const url = `${API_BASE}${path}`;
    const headers: Record<string, string> = {
      ...(opts.headers || {}),
    };
    if (!(body instanceof FormData)) {
      headers["Accept"] = "application/json";
    }
    if (body && !(body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    if (opts.idempotencyKey) {
      headers["X-Idempotency-Key"] = opts.idempotencyKey;
    }
    const currentUser = auth().currentUser;
    try {
      const token = await currentUser?.getIdToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    } catch {
      // ignore token fetch errors; proceed unauthenticated
    }
    const makeRequest = async () => {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(url, {
          method,
          headers,
          body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });
        if ([502, 503, 504].includes(res.status)) {
          throw Object.assign(new Error(`Transient error: ${res.status}`), {
            status: res.status,
          });
        }
        if (!res.ok) {
          throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status });
        }
        const text = await res.text();
        try {
          return text ? JSON.parse(text) : null;
        } catch {
          return text;
        }
      } finally {
        clearTimeout(id);
      }
    };

    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        return await makeRequest();
      } catch (err) {
        if (attempt === 1) throw err;
        await new Promise((r) => setTimeout(r, 200 + Math.random() * 300));
      }
    }
  }

  get(path: string) {
    return this.request("GET", path);
  }

  post(path: string, body: any, opts?: RequestOptions) {
    return this.request("POST", path, body, opts);
  }

  patch(path: string, body: any, opts?: RequestOptions) {
    return this.request("PATCH", path, body, opts);
  }

  upload(path: string, uri: string, opts?: RequestOptions) {
    const form = new FormData();
    form.append("file", { uri, name: "pod.jpg", type: "image/jpeg" } as any);
    return this.request("POST", path, form, opts);
  }
}

export default new ApiClient();

