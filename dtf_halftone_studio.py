import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk, ImageEnhance, ImageOps

APP_NAME = 'DTF Halftone Studio'

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.geometry('1120x760')
        root.minsize(850, 600)
        self.image = None
        self.result = None
        self.preview_photo = None
        self.path = ''
        self.zoom = 1.0
        self.preview_base = None
        self.dot = tk.IntVar(value=8)
        self.angle = tk.IntVar(value=45)
        self.contrast = tk.IntVar(value=120)
        self.threshold = tk.IntVar(value=5)
        self.mode = tk.StringVar(value='Black')
        self.transparent = tk.BooleanVar(value=True)
        self.invert = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        top = ttk.Frame(self.root, padding=8); top.pack(fill='x')
        ttk.Button(top, text='Open Image', command=self.open_image).pack(side='left')
        ttk.Button(top, text='Preview Effect', command=self.preview).pack(side='left', padx=(6,0))
        ttk.Button(top, text='Reset Image', command=self.reset_image).pack(side='left', padx=(6,0))
        ttk.Button(top, text='Clear Image', command=self.clear_image).pack(side='left', padx=(6,0))
        ttk.Button(top, text='Export High-Quality PNG', command=self.export).pack(side='left', padx=(6,0))
        self.filename = ttk.Label(top, text='No image selected'); self.filename.pack(side='left', padx=10)

        main = ttk.Frame(self.root, padding=(8,0,8,8)); main.pack(fill='both', expand=True)
        panel = ttk.LabelFrame(main, text='Halftone Settings', padding=10); panel.pack(side='left', fill='y')
        self._scale(panel, 'Dot size (pixels)', self.dot, 2, 40)
        self._scale(panel, 'Screen angle (degrees)', self.angle, 0, 90)
        self._scale(panel, 'Contrast (%)', self.contrast, 50, 200)
        self._scale(panel, 'Minimum ink threshold (%)', self.threshold, 0, 90)
        ttk.Label(panel, text='Ink / color mode').pack(anchor='w', pady=(12,3))
        ttk.Combobox(panel, textvariable=self.mode, values=['Black','White','Color','Grayscale'], state='readonly', width=18).pack(fill='x')
        ttk.Checkbutton(panel, text='Transparent background', variable=self.transparent).pack(anchor='w', pady=(12,3))
        ttk.Checkbutton(panel, text='Invert tones', variable=self.invert).pack(anchor='w')
        ttk.Button(panel, text='Reset Settings', command=self.reset_settings).pack(fill='x', pady=(12,2))
        ttk.Label(panel, text='Preview is scaled for speed.\nExport uses original image size.', wraplength=190).pack(anchor='w', pady=12)

        view = ttk.LabelFrame(main, text='Preview', padding=6); view.pack(side='left', fill='both', expand=True, padx=(10,0))
        tools = ttk.Frame(view); tools.pack(fill='x', pady=(0,5))
        ttk.Button(tools, text='− Zoom Out', command=self.zoom_out).pack(side='left')
        ttk.Button(tools, text='+ Zoom In', command=self.zoom_in).pack(side='left', padx=5)
        ttk.Button(tools, text='Fit to Window', command=self.fit_view).pack(side='left')
        self.zoom_label = ttk.Label(tools, text='100%'); self.zoom_label.pack(side='left', padx=10)
        canvas_frame = ttk.Frame(view); canvas_frame.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(canvas_frame, background='#e8e8e8', highlightthickness=0)
        self.hbar = ttk.Scrollbar(canvas_frame, orient='horizontal', command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew'); self.vbar.grid(row=0, column=1, sticky='ns'); self.hbar.grid(row=1, column=0, sticky='ew')
        canvas_frame.rowconfigure(0, weight=1); canvas_frame.columnconfigure(0, weight=1)
        self.canvas.create_text(250, 180, text='Open an image to begin', fill='#333333', tags='placeholder')
        self.canvas.bind('<Configure>', self._on_canvas_resize)
        self.status = tk.StringVar(value='Ready')
        ttk.Label(self.root, textvariable=self.status, relief='sunken', anchor='w', padding=5).pack(fill='x', side='bottom')

    def _scale(self, parent, label, var, low, high):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(8,0))
        row = ttk.Frame(parent); row.pack(fill='x')
        ttk.Scale(row, from_=low, to=high, variable=var, orient='horizontal').pack(side='left', fill='x', expand=True)
        val = ttk.Label(row, width=4, text=str(var.get())); val.pack(side='right')
        var.trace_add('write', lambda *_: val.configure(text=str(int(var.get()))))

    def open_image(self):
        p = filedialog.askopenfilename(title='Open image', filetypes=[('Image files','*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp'),('All files','*.*')])
        if not p: return
        try:
            with Image.open(p) as im: self.image = im.convert('RGBA')
            self.path = p; self.result = None; self.zoom = 1.0
            self.filename.configure(text=os.path.basename(p))
            self._set_preview(self.image)
            self.fit_view()
            self.status.set(f'Loaded {self.image.width} × {self.image.height}px')
        except Exception as e: messagebox.showerror('Open failed', str(e))

    def make_halftone(self, source):
        rgba = source.convert('RGBA'); rgb = rgba.convert('RGB')
        gray = ImageEnhance.Contrast(ImageOps.grayscale(rgb)).enhance(max(.1, self.contrast.get()/100))
        g = gray.load(); src = rgba.load(); w,h = rgba.size
        step = max(2, int(self.dot.get())); radius = step/2
        out = Image.new('RGBA', (w,h), (0,0,0,0) if self.transparent.get() else (255,255,255,255))
        draw = ImageDraw.Draw(out); angle = math.radians(self.angle.get()); ca,sa = math.cos(angle), math.sin(angle)
        extent = int(math.hypot(w,h)/2)+step; threshold = self.threshold.get()/100
        for sy in range(-extent, extent+step, step):
            for sx in range(-extent, extent+step, step):
                cx = int(w/2 + sx*ca - sy*sa); cy = int(h/2 + sx*sa + sy*ca)
                if cx < 0 or cy < 0 or cx >= w or cy >= h: continue
                alpha = src[cx,cy][3]/255
                if alpha < .03 and self.transparent.get(): continue
                ink = 1 - g[cx,cy]/255
                if self.invert.get(): ink = 1-ink
                if ink < threshold: continue
                rr = min(radius, math.sqrt(max(0,ink))*radius*1.40)
                if rr < .25: continue
                if self.mode.get() == 'White': color=(255,255,255,int(255*alpha))
                elif self.mode.get() == 'Color': color=(*src[cx,cy][:3], int(255*alpha))
                elif self.mode.get() == 'Grayscale':
                    v=int(255*(1-ink)); color=(v,v,v,int(255*alpha))
                else: color=(0,0,0,int(255*alpha))
                draw.ellipse((cx-rr,cy-rr,cx+rr,cy+rr), fill=color)
        return out

    def preview(self):
        if self.image is None:
            messagebox.showinfo('Open image','Please open an image first.'); return
        try:
            im = self.image.copy(); im.thumbnail((1200, 1000), Image.Resampling.LANCZOS)
            self.result = self.make_halftone(im); self._set_preview(self.result); self.fit_view()
            self.status.set('Preview ready. Export saves the full-resolution result.')
        except Exception as e: messagebox.showerror('Processing failed', str(e))

    def _set_preview(self, im):
        self.preview_base = im.copy()
        self._render_zoomed()

    def _render_zoomed(self):
        if self.preview_base is None: return
        w = max(1, int(self.preview_base.width*self.zoom)); h = max(1, int(self.preview_base.height*self.zoom))
        disp = self.preview_base.resize((w,h), Image.Resampling.LANCZOS)
        # Checkerboard background reveals transparency.
        bg = Image.new('RGBA', disp.size, (230,230,230,255)); d=ImageDraw.Draw(bg); tile=max(8,int(16*self.zoom))
        for y in range(0,bg.height,tile):
            for x in range(0,bg.width,tile):
                if (x//tile+y//tile)%2: d.rectangle((x,y,x+tile-1,y+tile-1), fill=(248,248,248,255))
        bg.alpha_composite(disp)
        self.preview_photo = ImageTk.PhotoImage(bg.convert('RGB'))
        self.canvas.delete('all')
        self.canvas.create_image(0,0,anchor='nw',image=self.preview_photo)
        self.canvas.configure(scrollregion=(0,0,w,h))
        self.zoom_label.configure(text=f'{int(self.zoom*100)}%')

    def zoom_in(self):
        if self.preview_base is None: return
        self.zoom=min(4.0,self.zoom*1.25); self._render_zoomed()

    def zoom_out(self):
        if self.preview_base is None: return
        self.zoom=max(0.1,self.zoom/1.25); self._render_zoomed()

    def fit_view(self):
        if self.preview_base is None: return
        self.root.update_idletasks()
        cw=max(100,self.canvas.winfo_width()-8); ch=max(100,self.canvas.winfo_height()-8)
        self.zoom=max(0.1,min(1.0,cw/self.preview_base.width,ch/self.preview_base.height))
        self._render_zoomed(); self.canvas.xview_moveto(0); self.canvas.yview_moveto(0)

    def _on_canvas_resize(self, _event):
        # Keep current zoom; user can press Fit to Window whenever desired.
        pass

    def reset_image(self):
        if self.image is None:
            self.status.set('No image to reset.'); return
        self.result = None; self._set_preview(self.image); self.fit_view()
        self.status.set('Original image restored. Preview effect has been cleared.')

    def clear_image(self):
        self.image = None; self.result = None; self.preview_base = None; self.path = ''; self.zoom = 1.0
        self.filename.configure(text='No image selected'); self.canvas.delete('all')
        self.canvas.configure(scrollregion=(0,0,0,0)); self.zoom_label.configure(text='100%')
        self.canvas.create_text(max(100,self.canvas.winfo_width()//2), max(80,self.canvas.winfo_height()//2), text='Open an image to begin', fill='#333333')
        self.status.set('Image cleared. Ready for a new image.')

    def reset_settings(self):
        self.dot.set(8); self.angle.set(45); self.contrast.set(120); self.threshold.set(5)
        self.mode.set('Black'); self.transparent.set(True); self.invert.set(False)
        self.status.set('Settings restored to defaults. Click Preview Effect to apply.')

    def export(self):
        if self.image is None:
            messagebox.showinfo('Open image','Please open an image first.'); return
        default = os.path.splitext(os.path.basename(self.path))[0] + '_DTF_Halftone.png'
        p = filedialog.asksaveasfilename(title='Export PNG', defaultextension='.png', initialfile=default, filetypes=[('PNG image','*.png')])
        if not p: return
        try:
            self.status.set('Rendering original-size image…'); self.root.update_idletasks()
            result = self.make_halftone(self.image); result.save(p, 'PNG', optimize=False)
            self.result = result; self._set_preview(result); self.fit_view()
            self.status.set(f'Exported: {p}')
            messagebox.showinfo('Export complete', f'PNG saved successfully.\nSize: {result.width} × {result.height}px\n\n{p}')
        except Exception as e: messagebox.showerror('Export failed', str(e)); self.status.set('Export failed')

if __name__ == '__main__':
    root = tk.Tk()
    try: ttk.Style().theme_use('vista')
    except tk.TclError: pass
    App(root); root.mainloop()
