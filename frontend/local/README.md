# Local Application Setup

This guide explains how to run the RAG Workflow application as a local desktop application.

## Option 1: Direct FastAPI with Browser

The simplest way to run locally is to use the FastAPI backend with the web frontend.

### Steps:

1. **Start OpenSearch** (if not already running):
   ```bash
   cd docker
   docker-compose up -d
   ```

2. **Configure Environment**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start the Backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

4. **Open the Frontend**:
   - Option A: Open `frontend/web/index.html` directly in your browser
   - Option B: Serve with a local web server:
     ```bash
     cd frontend/web
     python -m http.server 8080
     ```
     Then open `http://localhost:8080` in your browser

## Option 2: Electron Desktop App (Advanced)

For a more native desktop experience, you can wrap the application in Electron.

### Prerequisites:
- Node.js and npm installed
- Electron installed globally: `npm install -g electron`

### Setup:

1. **Create Electron Wrapper**:
   ```bash
   cd frontend/local
   npm init -y
   npm install electron --save-dev
   ```

2. **Create `main.js`** (Electron main process):
   ```javascript
   const { app, BrowserWindow } = require('electron');
   const path = require('path');
   
   function createWindow() {
     const win = new BrowserWindow({
       width: 1200,
       height: 800,
       webPreferences: {
         nodeIntegration: false,
         contextIsolation: true
       }
     });
     
     // Load the web frontend
     win.loadFile(path.join(__dirname, '../web/index.html'));
   }
   
   app.whenReady().then(createWindow);
   
   app.on('window-all-closed', () => {
     if (process.platform !== 'darwin') {
       app.quit();
     }
   });
   ```

3. **Update `package.json`**:
   ```json
   {
     "main": "main.js",
     "scripts": {
       "start": "electron ."
     }
   }
   ```

4. **Run**:
   ```bash
   npm start
   ```

## Option 3: Python Tkinter GUI (Alternative)

For a pure Python solution, you can create a Tkinter-based GUI.

### Create `frontend/local/tkinter_app.py`:

```python
import tkinter as tk
from tkinter import filedialog, scrolledtext
import requests
import os

API_BASE_URL = "http://localhost:8000"

class RAGApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RAG Workflow - RTG Scan Analysis")
        self.root.geometry("1000x700")
        
        self.setup_ui()
        self.current_file = None
        self.current_query_id = None
    
    def setup_ui(self):
        # File selection
        file_frame = tk.Frame(self.root, pady=10)
        file_frame.pack(fill=tk.X, padx=20)
        
        tk.Button(file_frame, text="Select File", command=self.select_file).pack(side=tk.LEFT)
        self.file_label = tk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        # Query button
        tk.Button(file_frame, text="Analyze", command=self.query, bg="#667eea", fg="white").pack(side=tk.LEFT, padx=10)
        
        # Results
        results_frame = tk.Frame(self.root)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(results_frame, text="Generated Description:", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        self.description_text = scrolledtext.ScrolledText(results_frame, height=10, wrap=tk.WORD)
        self.description_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tk.Label(results_frame, text="Retrieved Documents:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.retrieved_text = scrolledtext.ScrolledText(results_frame, height=8, wrap=tk.WORD)
        self.retrieved_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Regenerate button
        tk.Button(results_frame, text="Regenerate", command=self.regenerate).pack(pady=10)
    
    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("DICOM files", "*.dcm *.dicom"), ("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.file_label.config(text=os.path.basename(file_path))
    
    def query(self):
        if not self.current_file:
            tk.messagebox.showwarning("No File", "Please select a file first")
            return
        
        try:
            with open(self.current_file, 'rb') as f:
                files = {'file': f}
                data = {'use_retrieved_images': False}
                response = requests.post(f"{API_BASE_URL}/query", files=files, data=data)
            
            if response.ok:
                result = response.json()
                self.current_query_id = result['query_id']
                self.display_results(result)
            else:
                tk.messagebox.showerror("Error", response.json().get('detail', 'Query failed'))
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))
    
    def regenerate(self):
        if not self.current_query_id:
            tk.messagebox.showwarning("No Query", "Please run a query first")
            return
        
        try:
            data = {'query_id': self.current_query_id, 'use_same_retrieval': 'false'}
            files = {}
            if self.current_file:
                with open(self.current_file, 'rb') as f:
                    files['file'] = f
                    response = requests.post(f"{API_BASE_URL}/query/regenerate", files=files, data=data)
            else:
                response = requests.post(f"{API_BASE_URL}/query/regenerate", data=data)
            
            if response.ok:
                result = response.json()
                self.current_query_id = result['query_id']
                self.display_results(result)
            else:
                tk.messagebox.showerror("Error", response.json().get('detail', 'Regeneration failed'))
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))
    
    def display_results(self, result):
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, result.get('generated_description', 'No description'))
        
        self.retrieved_text.delete(1.0, tk.END)
        for i, doc in enumerate(result.get('retrieved_documents', []), 1):
            self.retrieved_text.insert(tk.END, f"Reference {i}:\n")
            self.retrieved_text.insert(tk.END, f"Score: {doc.get('score', 0):.4f}\n")
            self.retrieved_text.insert(tk.END, f"Description: {doc.get('full_description', 'N/A')}\n\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = RAGApp(root)
    root.mainloop()
```

### Run:
```bash
cd frontend/local
python tkinter_app.py
```

## Troubleshooting

- **CORS Issues**: If using the web frontend directly, make sure the FastAPI CORS settings allow your origin
- **API Connection**: Ensure the backend is running on `http://localhost:8000`
- **File Access**: Some browsers restrict local file access; use a local web server instead

## Recommended Approach

For most users, **Option 1** (FastAPI + Browser) is the simplest and most reliable approach. It provides a good user experience without additional complexity.

