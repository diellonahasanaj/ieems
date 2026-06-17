import os
import requests

# Konfigurimi i URL-së së serverit FastAPI dhe ID-së së testimit
BASE_URL = "http://127.0.0.1:8000"
RUN_ID = "test_run_123"

def test_ieems_pipeline():
    print("\n--- [TEST] Duke nisur testimin e integrimit të IEEMS ---")

    # 1. Krijo një faturë të thjeshtë simuluese (dummy file) lokale për ta ngarkuar
    dummy_filename = "fatura_test.txt"
    with open(dummy_filename, "w") as f:
        f.write("Fature Test: Giga Academy - Shuma 1250 EUR - Qendra e Kostos: RND")

    # Hapim skedarin për t'ia dërguar API-së
    with open(dummy_filename, "rb") as f:
        files = {"file": (dummy_filename, f, "text/plain")}
        params = {"run_id": RUN_ID}
        
        try:
            # Dërgimi i kërkesës te endpoint-i /upload
            upload_response = requests.post(f"{BASE_URL}/upload", files=files, params=params)
            if upload_response.status_code == 200:
                print("✅ Hapi 1: Endpoint-i i ngarkimit (/upload) u përgjigj me sukses.")
            else:
                print(f"❌ Hapi 1: Ngarkimi dështoi me status kodin: {upload_response.status_code}")
                return
        except requests.exceptions.ConnectionError:
            print("\n❌ GABIM: Nuk mund të lidhem me serverin FastAPI.")
            print("Sigurohu që serveri uvicorn është i ndezur dhe po dëgjon në http://127.0.0.1:8000\n")
            return

    # Pastrojmë skedarin dummy lokal pasi e dërguam me sukses në server
    if os.path.exists(dummy_filename):
        os.remove(dummy_filename)

    # 2. Triggerimi i ekzekutimit të Pipeline-it me LangGraph
    print("\n--- [TEST] Duke aktivizuar ekzekutimin e LangGraph Pipeline ---")
    run_params = {
        "run_id": RUN_ID,
        "employee_id": "EMP_DIELONA_01",
        "cost_center": "RND"
    }
    
    run_response = requests.post(f"{BASE_URL}/run", params=run_params)
    
    if run_response.status_code == 200:
        print("✅ Hapi 2: Workflow i LangGraph u ekzekutua deri në fund.")
        print(f"   Payload i përgjigjes: {run_response.json()}")
    else:
        print(f"❌ Hapi 2: Ekzekutimi i pipeline dështoi me status kodin: {run_response.status_code}")
        return

    # 3. Verifikimi i gjenerimit të skedarëve të Auditimit (JSON Packets)
    print("\n--- [TEST] Duke verifikuar gjenerimin e skedarëve të auditimit ---")
    
    # Rruga e saktë relative: shkon një folder prapa (te rrënja) dhe futet te backend
    meta_path = f"../backend/run_storage/{RUN_ID}/metadata"
    
    context_file = os.path.join(meta_path, "context_packet.json")
    approval_file = os.path.join(meta_path, "approval_packet.json")

    # Kontrolli për context_packet.json
    if os.path.exists(context_file):
        print(f"✅ U gjet skedari i auditimit: {context_file}")
    else:
        print(f"❌ Mungon skedari i pritur: {context_file}")

    # Kontrolli për approval_packet.json
    if os.path.exists(approval_file):
        print(f"✅ U gjet skedari i auditimit: {approval_file}")
    else:
        print(f"❌ Mungon skedari i pritur: {approval_file}")
    print("\n--- [TEST] Testimi përfundoi ---")

if __name__ == "__main__":
    test_ieems_pipeline()