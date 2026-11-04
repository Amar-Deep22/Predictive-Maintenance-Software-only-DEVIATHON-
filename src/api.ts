export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, {method, headers:{"Content-Type":"application/json","X-Meridian-Client":"portal"}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  if (!response.ok) { const data = await response.json().catch(()=>null); throw new Error(typeof data?.detail === "string" ? data.detail : `Request failed (${response.status})`); }
  return response.json();
}
