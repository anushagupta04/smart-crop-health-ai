import os

base_dir = r'C:/Users/KIIT0001/Documents/smart-crop-health'

def fix_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        new_content = content.replace(b'\xe2\x80\x94', b'-').replace(b'\xe2\x80\x93', b'-')
        if b'\xe2\x80\x94' in content or b'\xe2\x80\x93' in content:
            with open(filepath, 'wb') as f:
                f.write(new_content)
            print(f'Fixed {filepath}')
        else:
            print(f'No changes needed for {filepath}')
    except Exception as e:
        print(f'Error processing {filepath}: {e}')

fix_file(os.path.join(base_dir, 'app.py'))
fix_file(os.path.join(base_dir, 'recomendation.py'))
fix_file(os.path.join(base_dir, 'frontend/app.js'))
print("Done")
