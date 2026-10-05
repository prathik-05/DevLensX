import os, sys, base64

def write(rel_path: str, content: str | bytes):
    data = content.encode('utf-8') if isinstance(content, str) else content
    for base in ['d:/projects/DevLensX', 'C:/Users/SVCS/Desktop/DevLensX']:
        full_path = os.path.join(base, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(data)
        print(f'Wrote {rel_path} to {full_path}')

if __name__ == '__main__':
    if len(sys.argv) > 2:
        rel_path = sys.argv[1]
        data = base64.b64decode(sys.argv[2])
        write(rel_path, data)
