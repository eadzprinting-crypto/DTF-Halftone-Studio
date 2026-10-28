import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk, ImageEnhance, ImageOps

APP_NAME = 'DTF Halftone Studio'

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME + ' — Embroidery Preview')
        root.geometry('1180x800')
        root.minsize(900, 620)
        self.image = None; self.result = None; self.preview_photo = None; self.path = ''
        self.zoom = 1.0; self.preview_base = None; self.preview_kind = 'image'
        self.dot = tk.IntVar(value=8); self.angle = tk.IntVar(value=45)
        self.contrast = tk.IntVar(value=120); self.threshold = tk.IntVar(value=5)
        self.mode = tk.StringVar(value='Black'); self.transparent = tk.BooleanVar(value=True); self.invert = tk.BooleanVar(value=False)
        self.emb_width = tk.IntVar(value=100); self.stitch_spacing = tk.DoubleVar(value=1.5); self.emb_threshold = tk.IntVar(value=55)
        self._build()

    def _build(self):
        top=ttk.Frame(self.root,padding=8); top.pack(fill='x')
        for label,cmd in [('Open Image',self.open_image),('Preview Halftone',self.preview),('Reset Image',self.reset_image),('Clear Image',self.clear_image),('Export PNG',self.export),('Embroidery Preview',self.embroidery_preview),('Export DST',lambda:self.export_embroidery('dst')),('Export PES',lambda:self.export_embroidery('pes'))]:
            ttk.Button(top,text=label,command=cmd).pack(side='left',padx=(0,5))
        self.filename=ttk.Label(top,text='No image selected'); self.filename.pack(side='left',padx=6)
        main=ttk.Frame(self.root,padding=(8,0,8,8)); main.pack(fill='both',expand=True)
        panel=ttk.LabelFrame(main,text='Settings',padding=10); panel.pack(side='left',fill='y')
        ttk.Label(panel,text='HALFTONE').pack(anchor='w',pady=(0,3))
        self._scale(panel,'Dot size (pixels)',self.dot,2,40)
        self._scale(panel,'Screen angle (degrees)',self.angle,0,90)
        self._scale(panel,'Contrast (%)',self.contrast,50,200)
        self._scale(panel,'Minimum ink threshold (%)',self.threshold,0,90)
        ttk.Label(panel,text='Ink / color mode').pack(anchor='w',pady=(10,3))
        ttk.Combobox(panel,textvariable=self.mode,values=['Black','White','Color','Grayscale'],state='readonly',width=18).pack(fill='x')
        ttk.Checkbutton(panel,text='Transparent background',variable=self.transparent).pack(anchor='w',pady=(8,2))
        ttk.Checkbutton(panel,text='Invert tones',variable=self.invert).pack(anchor='w')
        ttk.Button(panel,text='Reset Halftone Settings',command=self.reset_settings).pack(fill='x',pady=(8,12))
        ttk.Separator(panel).pack(fill='x',pady=4)
        ttk.Label(panel,text='EMBROIDERY (approximate)',foreground='#155e75').pack(anchor='w',pady=(4,2))
        self._scale(panel,'Design width (mm)',self.emb_width,30,180)
        self._scale(panel,'Stitch row spacing (mm)',self.stitch_spacing,0.8,4.0,fmt=lambda x:f'{x:.1f}')
        self._scale(panel,'Darkness threshold (%)',self.emb_threshold,10,90)
        ttk.Label(panel,text='Embroidery export uses a basic raster running-stitch approximation. It is NOT professional auto-digitizing.',wraplength=205,foreground='#9a3412').pack(anchor='w',pady=(8,3))
        ttk.Button(panel,text='Reset Embroidery Settings',command=self.reset_emb_settings).pack(fill='x',pady=4)
        view=ttk.LabelFrame(main,text='Preview',padding=6); view.pack(side='left',fill='both',expand=True,padx=(10,0))
        tools=ttk.Frame(view); tools.pack(fill='x',pady=(0,5))
        ttk.Button(tools,text='− Zoom Out',command=self.zoom_out).pack(side='left')
        ttk.Button(tools,text='+ Zoom In',command=self.zoom_in).pack(side='left',padx=5)
        ttk.Button(tools,text='Fit to Window',command=self.fit_view).pack(side='left')
        self.zoom_label=ttk.Label(tools,text='100%'); self.zoom_label.pack(side='left',padx=10)
        cf=ttk.Frame(view); cf.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(cf,background='#e8e8e8',highlightthickness=0)
        self.hbar=ttk.Scrollbar(cf,orient='horizontal',command=self.canvas.xview); self.vbar=ttk.Scrollbar(cf,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set,yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0,column=0,sticky='nsew'); self.vbar.grid(row=0,column=1,sticky='ns'); self.hbar.grid(row=1,column=0,sticky='ew')
        cf.rowconfigure(0,weight=1); cf.columnconfigure(0,weight=1)
        self.canvas.create_text(250,180,text='Open an image to begin',fill='#333',tags='placeholder')
        self.canvas.bind('<Configure>',self._on_canvas_resize)
        self.status=tk.StringVar(value='Ready'); ttk.Label(self.root,textvariable=self.status,relief='sunken',anchor='w',padding=5).pack(fill='x',side='bottom')

    def _scale(self,parent,label,var,low,high,fmt=None):
        ttk.Label(parent,text=label).pack(anchor='w',pady=(6,0)); row=ttk.Frame(parent); row.pack(fill='x')
        ttk.Scale(row,from_=low,to=high,variable=var,orient='horizontal').pack(side='left',fill='x',expand=True)
        val=ttk.Label(row,width=5,text=str(var.get())); val.pack(side='right')
        def update(*_):
            v=var.get(); val.configure(text=fmt(v) if fmt else str(int(float(v))))
        var.trace_add('write',update)

    def open_image(self):
        p=filedialog.askopenfilename(title='Open image',filetypes=[('Image files','*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp'),('All files','*.*')])
        if not p:return
        try:
            with Image.open(p) as im:self.image=im.convert('RGBA')
            self.path=p; self.result=None; self.zoom=1.0; self.filename.configure(text=os.path.basename(p)); self._set_preview(self.image,'image'); self.fit_view()
            self.status.set(f'Loaded {self.image.width} × {self.image.height}px')
        except Exception as e:messagebox.showerror('Open failed',str(e))

    def make_halftone(self,source):
        rgba=source.convert('RGBA'); gray=ImageEnhance.Contrast(ImageOps.grayscale(rgba.convert('RGB'))).enhance(max(.1,self.contrast.get()/100))
        g=gray.load(); src=rgba.load(); w,h=rgba.size; step=max(2,int(self.dot.get())); radius=step/2
        out=Image.new('RGBA',(w,h),(0,0,0,0) if self.transparent.get() else (255,255,255,255)); draw=ImageDraw.Draw(out)
        angle=math.radians(self.angle.get()); ca,sa=math.cos(angle),math.sin(angle); extent=int(math.hypot(w,h)/2)+step; threshold=self.threshold.get()/100
        for sy in range(-extent,extent+step,step):
            for sx in range(-extent,extent+step,step):
                cx=int(w/2+sx*ca-sy*sa); cy=int(h/2+sx*sa+sy*ca)
                if cx<0 or cy<0 or cx>=w or cy>=h:continue
                alpha=src[cx,cy][3]/255
                if alpha<.03 and self.transparent.get():continue
                ink=1-g[cx,cy]/255
                if self.invert.get():ink=1-ink
                if ink<threshold:continue
                rr=min(radius,math.sqrt(max(0,ink))*radius*1.4)
                if rr<.25:continue
                if self.mode.get()=='White':color=(255,255,255,int(255*alpha))
                elif self.mode.get()=='Color':color=(*src[cx,cy][:3],int(255*alpha))
                elif self.mode.get()=='Grayscale':
                    v=int(255*(1-ink)); color=(v,v,v,int(255*alpha))
                else:color=(0,0,0,int(255*alpha))
                draw.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=color)
        return out

    def preview(self):
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return
        try:
            im=self.image.copy(); im.thumbnail((1200,1000),Image.Resampling.LANCZOS); self.result=self.make_halftone(im); self._set_preview(self.result,'halftone'); self.fit_view()
            self.status.set('Halftone preview ready. PNG export uses original dimensions.')
        except Exception as e:messagebox.showerror('Processing failed',str(e))

    def make_embroidery_preview(self):
        if self.image is None:return None
        im=self.image.copy(); im.thumbnail((700,600),Image.Resampling.LANCZOS); rgba=im.convert('RGBA'); gray=ImageOps.grayscale(rgba.convert('RGB'))
        # Stylized simulation only: thread-like short line segments on dark regions.
        out=Image.new('RGBA',rgba.size,(246,242,232,255)); d=ImageDraw.Draw(out); pix=gray.load(); step=max(3,int(self.stitch_spacing.get()*3.5))
        for y in range(2,rgba.height-2,step):
            reverse=((y//step)%2)==1
            xs=list(range(2,rgba.width-2,5))
            if reverse:xs.reverse()
            for x in xs:
                if pix[x,y] < int(255*self.emb_threshold.get()/100):
                    x2=min(rgba.width-2,x+(3 if not reverse else -3)); y2=min(rgba.height-2,y+2)
                    d.line((x,y,x2,y2),fill=(28,42,60,255),width=1)
        return out

    def embroidery_preview(self):
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return
        self._set_preview(self.make_embroidery_preview(),'embroidery'); self.fit_view()
        self.status.set('Embroidery-style preview shown (visual simulation, not a stitch-accurate machine simulation).')

    def build_pattern(self):
        try:
            from pyembroidery import EmbPattern, STITCH, JUMP, END, write_dst, write_pes
        except ImportError:
            messagebox.showerror('Embroidery dependency missing','pyembroidery is not installed. Rebuild the EXE from the updated GitHub workflow; it now installs pyembroidery.')
            return None
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return None
        # Simple monochrome raster running-stitch approximation. This does not understand satin columns, object boundaries, pull compensation or underlay.
        src=self.image.copy().convert('RGB'); target_w=max(30,min(180,int(self.emb_width.get())))
        target_h=max(1,round(target_w*src.height/src.width)); src=src.resize((max(1,int(target_w*3)),max(1,int(target_h*3))),Image.Resampling.LANCZOS)
        gray=ImageOps.grayscale(src); px=gray.load(); w,h=gray.size
        pattern=EmbPattern(); row_px=max(2,int(self.stitch_spacing.get()*3)); stitch_px=3 # approx 1 mm per point in design coordinates
        threshold=int(255*self.emb_threshold.get()/100); count=0; max_stitches=60000
        for yi,y in enumerate(range(0,h,row_px)):
            xs=list(range(0,w,stitch_px))
            if yi%2:xs.reverse()
            row_points=[]
            for x in xs:
                if px[x,y] < threshold:row_points.append((x/3.0,y/3.0))
            if not row_points:continue
            # Separate sparse dark pixels into runs to reduce jumps.
            runs=[]; run=[]; prev=None
            for point in row_points:
                if prev is not None and abs(point[0]-prev[0]) > 2.1:
                    if run:runs.append(run)
                    run=[]
                run.append(point); prev=point
            if run:runs.append(run)
            for run in runs:
                if not run:continue
                x,y0=run[0]
                pattern.add_stitch_absolute(JUMP,x,y0)
                for x,y0 in run[1:]:
                    pattern.add_stitch_absolute(STITCH,x,y0); count+=1
                    if count>=max_stitches:break
                if count>=max_stitches:break
            if count>=max_stitches:break
        pattern.add_stitch_absolute(END,0,0)
        if count<20:
            messagebox.showwarning('Few stitches','Threshold produced very few stitches. Try lowering Darkness threshold or use a darker, higher-contrast image.')
        self.status.set(f'Approximate stitch path generated: {count:,} stitches. Verify in embroidery software before machine use.')
        return pattern

    def export_embroidery(self,fmt):
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return
        try:
            from pyembroidery import write_dst, write_pes
        except ImportError:
            messagebox.showerror('Embroidery dependency missing','pyembroidery is not installed. Rebuild the EXE from GitHub Actions after committing the updated requirements.txt.');return
        p=filedialog.asksaveasfilename(title=f'Export embroidery {fmt.upper()}',defaultextension='.'+fmt,initialfile=os.path.splitext(os.path.basename(self.path))[0]+'_approx.'+fmt,filetypes=[(fmt.upper()+' embroidery file','*.'+fmt)])
        if not p:return
        try:
            pattern=self.build_pattern()
            if pattern is None:return
            if fmt=='dst':write_dst(pattern,p)
            else:write_pes(pattern,p)
            messagebox.showwarning('Exported — inspect before production',f'Created {fmt.upper()} file:\n{p}\n\nIMPORTANT: This is a basic monochrome raster running-stitch approximation, not professional auto-digitizing. Inspect stitch count, size, jumps, trims and machine compatibility in your embroidery software before sewing.')
            self.status.set('Embroidery file exported; professional verification required.')
        except Exception as e:messagebox.showerror('Embroidery export failed',str(e))

    def _set_preview(self,im,kind='image'):
        self.preview_base=im.copy(); self.preview_kind=kind; self._render_zoomed()
    def _render_zoomed(self):
        if self.preview_base is None:return
        w=max(1,int(self.preview_base.width*self.zoom)); h=max(1,int(self.preview_base.height*self.zoom)); disp=self.preview_base.resize((w,h),Image.Resampling.LANCZOS)
        bg=Image.new('RGBA',disp.size,(230,230,230,255)); d=ImageDraw.Draw(bg); tile=max(8,int(16*self.zoom))
        for y in range(0,bg.height,tile):
            for x in range(0,bg.width,tile):
                if (x//tile+y//tile)%2:d.rectangle((x,y,x+tile-1,y+tile-1),fill=(248,248,248,255))
        bg.alpha_composite(disp); self.preview_photo=ImageTk.PhotoImage(bg.convert('RGB')); self.canvas.delete('all')
        self.canvas.create_image(0,0,anchor='nw',image=self.preview_photo); self.canvas.configure(scrollregion=(0,0,w,h)); self.zoom_label.configure(text=f'{int(self.zoom*100)}%')
    def zoom_in(self):
        if self.preview_base is not None:self.zoom=min(4.0,self.zoom*1.25);self._render_zoomed()
    def zoom_out(self):
        if self.preview_base is not None:self.zoom=max(.1,self.zoom/1.25);self._render_zoomed()
    def fit_view(self):
        if self.preview_base is None:return
        self.root.update_idletasks(); cw=max(100,self.canvas.winfo_width()-8); ch=max(100,self.canvas.winfo_height()-8)
        self.zoom=max(.1,min(1.0,cw/self.preview_base.width,ch/self.preview_base.height)); self._render_zoomed(); self.canvas.xview_moveto(0); self.canvas.yview_moveto(0)
    def _on_canvas_resize(self,_event):pass
    def reset_image(self):
        if self.image is None:self.status.set('No image to reset.');return
        self.result=None;self._set_preview(self.image,'image');self.fit_view();self.status.set('Original image restored.')
    def clear_image(self):
        self.image=None;self.result=None;self.preview_base=None;self.path='';self.zoom=1.0;self.filename.configure(text='No image selected');self.canvas.delete('all');self.canvas.configure(scrollregion=(0,0,0,0));self.zoom_label.configure(text='100%');self.status.set('Image cleared. Ready for a new image.')
    def reset_settings(self):
        self.dot.set(8);self.angle.set(45);self.contrast.set(120);self.threshold.set(5);self.mode.set('Black');self.transparent.set(True);self.invert.set(False);self.status.set('Halftone settings reset.')
    def reset_emb_settings(self):
        self.emb_width.set(100);self.stitch_spacing.set(1.5);self.emb_threshold.set(55);self.status.set('Embroidery settings reset.')
    def export(self):
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return
        default=os.path.splitext(os.path.basename(self.path))[0]+'_DTF_Halftone.png';p=filedialog.asksaveasfilename(title='Export PNG',defaultextension='.png',initialfile=default,filetypes=[('PNG image','*.png')])
        if not p:return
        try:
            self.status.set('Rendering original-size image…');self.root.update_idletasks();result=self.make_halftone(self.image);result.save(p,'PNG',optimize=False);self.result=result;self._set_preview(result,'halftone');self.fit_view();self.status.set(f'Exported: {p}')
            messagebox.showinfo('Export complete',f'PNG saved successfully.\nSize: {result.width} × {result.height}px\n\n{p}')
        except Exception as e:messagebox.showerror('Export failed',str(e));self.status.set('Export failed')

if __name__=='__main__':
    root=tk.Tk()
    try:ttk.Style().theme_use('vista')
    except tk.TclError:pass
    App(root);root.mainloop()
