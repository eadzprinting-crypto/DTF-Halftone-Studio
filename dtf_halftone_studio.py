import math
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk, ImageEnhance, ImageOps

APP_NAME = 'DTF Halftone Studio'

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.geometry('980x720')
        root.minsize(800, 600)
        self.image = None
        self.result = None
        self.preview_photo = None
        self.path = ''
        self.dot = tk.IntVar(value=8)
        self.angle = tk.IntVar(value=45)
        self.contrast = tk.IntVar(value=120)
        self.threshold = tk.IntVar(value=5)
        self.mode = tk.StringVar(value='Black')
        self.transparent = tk.BooleanVar(value=True)
        self.invert = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        top = ttk.Frame(self.root, padding=10); top.pack(fill='x')
        ttk.Button(top, text='Open Image', command=self.open_image).pack(side='left')
        ttk.Button(top, text='Preview Effect', command=self.preview).pack(side='left', padx=8)
        ttk.Button(top, text='Export High-Quality PNG', command=self.export).pack(side='left')
        self.filename = ttk.Label(top, text='No image selected'); self.filename.pack(side='left', padx=12)
        main = ttk.Frame(self.root, padding=(10,0,10,10)); main.pack(fill='both', expand=True)
        panel = ttk.LabelFrame(main, text='Halftone Settings', padding=12); panel.pack(side='left', fill='y')
        self._scale(panel, 'Dot size (pixels)', self.dot, 2, 40)
        self._scale(panel, 'Screen angle (degrees)', self.angle, 0, 90)
        self._scale(panel, 'Contrast (%)', self.contrast, 50, 200)
        self._scale(panel, 'Minimum ink threshold (%)', self.threshold, 0, 90)
        ttk.Label(panel, text='Ink / color mode').pack(anchor='w', pady=(12,3))
        ttk.Combobox(panel, textvariable=self.mode, values=['Black','White','Color','Grayscale'], state='readonly', width=18).pack(fill='x')
        ttk.Checkbutton(panel, text='Transparent background', variable=self.transparent).pack(anchor='w', pady=(12,3))
        ttk.Checkbutton(panel, text='Invert tones', variable=self.invert).pack(anchor='w')
        ttk.Label(panel, text='Preview is scaled for speed.\nExport uses the original image size.', wraplength=190).pack(anchor='w', pady=18)
        view = ttk.LabelFrame(main, text='Preview', padding=8); view.pack(side='left', fill='both', expand=True, padx=(12,0))
        self.preview_label = ttk.Label(view, text='Open an image to begin', anchor='center')
        self.preview_label.pack(fill='both', expand=True)
        self.status = tk.StringVar(value='Ready')
        ttk.Label(self.root, textvariable=self.status, relief='sunken', anchor='w', padding=5).pack(fill='x', side='bottom')

    def _scale(self, parent, label, var, low, high):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(8,0))
        row = ttk.Frame(parent); row.pack(fill='x')
        scale = ttk.Scale(row, from_=low, to=high, variable=var, orient='horizontal')
        scale.pack(side='left', fill='x', expand=True)
        val = ttk.Label(row, width=4, text=str(var.get())); val.pack(side='right')
        def update(*_): val.configure(text=str(int(var.get())))
        var.trace_add('write', update)

    def open_image(self):
        p = filedialog.askopenfilename(title='Open image', filetypes=[('Image files','*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp'),('All files','*.*')])
        if not p: return
        try:
            im = Image.open(p)
            self.image = im.convert('RGBA')
            self.path = p
            self.result = None
            self.filename.configure(text=os.path.basename(p))
            self._show(self.image)
            self.status.set(f'Loaded {self.image.width} × {self.image.height}px')
        except Exception as e:
            messagebox.showerror('Open failed', str(e))

    def make_halftone(self, source):
        rgba = source.convert('RGBA')
        rgb = rgba.convert('RGB')
        gray = ImageOps.grayscale(rgb)
        gray = ImageEnhance.Contrast(gray).enhance(max(.1, self.contrast.get()/100))
        g = gray.load(); src = rgba.load(); w,h = rgba.size
        step = max(2, int(self.dot.get())); radius = step/2
        # Render on a transparent canvas; sample cells in a rotated screen coordinate system.
        out = Image.new('RGBA', (w,h), (0,0,0,0) if self.transparent.get() else (255,255,255,255))
        draw = ImageDraw.Draw(out)
        angle = math.radians(self.angle.get()); ca,sa = math.cos(angle), math.sin(angle)
        corners = [(-w/2,-h/2),(w/2,-h/2),(-w/2,h/2),(w/2,h/2)]
        extent = int(math.hypot(w,h)/2)+step
        threshold = self.threshold.get()/100
        for sy in range(-extent, extent+step, step):
            for sx in range(-extent, extent+step, step):
                # rotate screen grid into image coordinates
                cx = int(w/2 + sx*ca - sy*sa); cy = int(h/2 + sx*sa + sy*ca)
                if cx < 0 or cy < 0 or cx >= w or cy >= h: continue
                alpha = src[cx,cy][3]/255
                if alpha < .03 and self.transparent.get(): continue
                lum = g[cx,cy]/255
                ink = 1-lum
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
            im = self.image.copy()
            im.thumbnail((1000, 760), Image.Resampling.LANCZOS)
            self.result = self.make_halftone(im)
            self._show(self.result)
            self.status.set('Preview ready. Export to save full-resolution PNG.')
        except Exception as e: messagebox.showerror('Processing failed', str(e))

    def _show(self, im):
        preview = im.copy(); preview.thumbnail((700,560), Image.Resampling.LANCZOS)
        # checkerboard background makes transparency visible
        bg = Image.new('RGBA', preview.size, (225,225,225,255)); d=ImageDraw.Draw(bg)
        tile=16
        for y in range(0,bg.height,tile):
            for x in range(0,bg.width,tile):
                if (x//tile+y//tile)%2: d.rectangle((x,y,x+tile-1,y+tile-1), fill=(245,245,245,255))
        bg.alpha_composite(preview)
        self.preview_photo = ImageTk.PhotoImage(bg.convert('RGB'))
        self.preview_label.configure(image=self.preview_photo, text='')

    def export(self):
        if self.image is None:
            messagebox.showinfo('Open image','Please open an image first.'); return
        default = os.path.splitext(os.path.basename(self.path))[0] + '_DTF_Halftone.png'
        p = filedialog.asksaveasfilename(title='Export PNG', defaultextension='.png', initialfile=default, filetypes=[('PNG image','*.png')])
        if not p: return
        try:
            self.status.set('Rendering original-size image…'); self.root.update_idletasks()
            result = self.make_halftone(self.image)
            result.save(p, 'PNG', optimize=False)
            self.result = result
            self._show(result)
            self.status.set(f'Exported: {p}')
            messagebox.showinfo('Export complete', f'PNG saved successfully.\nSize: {result.width} × {result.height}px\n\n{p}')
        except Exception as e: messagebox.showerror('Export failed', str(e)); self.status.set('Export failed')

if __name__ == '__main__':
    root = tk.Tk()
    try: ttk.Style().theme_use('vista')
    except tk.TclError: pass
    App(root)
    root.mainloop()
