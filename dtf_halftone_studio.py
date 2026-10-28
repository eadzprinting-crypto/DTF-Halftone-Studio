import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
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
        self.stitch_type = tk.StringVar(value='Fill / Tatami (approx.)'); self.stitch_length = tk.DoubleVar(value=3.0); self.underlay = tk.BooleanVar(value=True); self.thread_palette = ['#202020', '#D62828', '#2474D2', '#F2C230', '#FFFFFF']; self.selected_thread = tk.StringVar(value='#202020'); self.region_mappings = []; self.sampled_rgb = None
        self._build()

    def _build(self):
        top=ttk.Frame(self.root,padding=8); top.pack(fill='x')
        for label,cmd in [('Open Image',self.open_image),('Preview Effect',self.preview),('Reset Image',self.reset_image),('Clear Image',self.clear_image),('Export PNG',self.export)]:
            ttk.Button(top,text=label,command=cmd).pack(side='left',padx=(0,5))
        self.filename=ttk.Label(top,text='No image selected'); self.filename.pack(side='left',padx=6)
        main=ttk.Frame(self.root,padding=(8,0,8,8)); main.pack(fill='both',expand=True)
        left=ttk.Frame(main,width=300); left.pack(side='left',fill='y'); left.pack_propagate(False)
        self.tabs=ttk.Notebook(left); self.tabs.pack(fill='both',expand=True)
        dtf=ttk.Frame(self.tabs,padding=10); self.tabs.add(dtf,text='DTF Halftone')
        ttk.Label(dtf,text='HALFTONE SETTINGS').pack(anchor='w',pady=(0,3))
        self._scale(dtf,'Dot size (pixels)',self.dot,2,40)
        self._scale(dtf,'Screen angle (degrees)',self.angle,0,90)
        self._scale(dtf,'Contrast (%)',self.contrast,50,200)
        self._scale(dtf,'Minimum ink threshold (%)',self.threshold,0,90)
        ttk.Label(dtf,text='Ink / color mode').pack(anchor='w',pady=(10,3))
        ttk.Combobox(dtf,textvariable=self.mode,values=['Black','White','Color','Grayscale'],state='readonly').pack(fill='x')
        ttk.Checkbutton(dtf,text='Transparent background',variable=self.transparent).pack(anchor='w',pady=(8,2))
        ttk.Checkbutton(dtf,text='Invert tones',variable=self.invert).pack(anchor='w')
        ttk.Button(dtf,text='Preview Halftone',command=self.preview).pack(fill='x',pady=(10,4))
        ttk.Button(dtf,text='Reset Halftone Settings',command=self.reset_settings).pack(fill='x')

        emb=ttk.Frame(self.tabs,padding=10); self.tabs.add(emb,text='Embroidery Studio')
        ttk.Label(emb,text='DESIGN & STITCH SETTINGS',font=('Segoe UI',9,'bold')).pack(anchor='w')
        self._scale(emb,'Design width (mm)',self.emb_width,20,250)
        self._scale(emb,'Stitch row spacing (mm)',self.stitch_spacing,0.4,4.0,fmt=lambda x:f'{x:.1f}')
        self._scale(emb,'Maximum stitch length (mm)',self.stitch_length,1.0,6.0,fmt=lambda x:f'{x:.1f}')
        ttk.Label(emb,text='Stitch type').pack(anchor='w',pady=(8,2))
        ttk.Combobox(emb,textvariable=self.stitch_type,values=['Running Stitch','Fill / Tatami (approx.)','Satin-like Zigzag (approx.)'],state='readonly').pack(fill='x')
        self._scale(emb,'Darkness threshold (%)',self.emb_threshold,5,95)
        ttk.Checkbutton(emb,text='Add simple underlay pass (approx.)',variable=self.underlay).pack(anchor='w',pady=5)
        ttk.Button(emb,text='Preview Embroidery',command=self.embroidery_preview).pack(fill='x',pady=(4,3))
        ttk.Button(emb,text='Reset Embroidery Settings',command=self.reset_emb_settings).pack(fill='x',pady=3)
        ttk.Separator(emb).pack(fill='x',pady=8)
        ttk.Label(emb,text='THREAD COLOR MANAGEMENT',font=('Segoe UI',9,'bold')).pack(anchor='w')
        self.thread_list=tk.Listbox(emb,height=5,exportselection=False); self.thread_list.pack(fill='x',pady=4)
        self._refresh_thread_list()
        buttons=ttk.Frame(emb); buttons.pack(fill='x')
        ttk.Button(buttons,text='Add Color',command=self.add_thread_color).pack(side='left',fill='x',expand=True)
        ttk.Button(buttons,text='Edit Color',command=self.edit_thread_color).pack(side='left',fill='x',expand=True,padx=3)
        ttk.Button(buttons,text='Remove',command=self.remove_thread_color).pack(side='left',fill='x',expand=True)
        ttk.Label(emb,text='PHOTO REGION → THREAD COLOR MAPPING',font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(10,2))
        ttk.Label(emb,text='Click a region in the preview, select a thread above, then assign it to that sampled color.',wraplength=270).pack(anchor='w')
        self.mapping_list=tk.Listbox(emb,height=4,exportselection=False); self.mapping_list.pack(fill='x',pady=4)
        maprow=ttk.Frame(emb); maprow.pack(fill='x')
        ttk.Button(maprow,text='Sample from Preview',command=self.enable_sample).pack(side='left',fill='x',expand=True)
        ttk.Button(maprow,text='Assign Thread',command=self.assign_region_thread).pack(side='left',fill='x',expand=True,padx=3)
        ttk.Button(maprow,text='Remove Map',command=self.remove_region_map).pack(side='left',fill='x',expand=True)
        self.sample_mode=False
        self.canvas.bind('<Button-1>',self._sample_canvas_color)
        ttk.Label(emb,text='DST supports limited color-change records; PES support varies by machine/software. Color-region mapping is approximate; output is algorithmic raster stitching, not professional object-based digitizing.',wraplength=260,foreground='#9a3412').pack(anchor='w',pady=(8,3))
        exportrow=ttk.Frame(emb); exportrow.pack(fill='x',pady=4)
        ttk.Button(exportrow,text='Export DST',command=lambda:self.export_embroidery('dst')).pack(side='left',fill='x',expand=True)
        ttk.Button(exportrow,text='Export PES',command=lambda:self.export_embroidery('pes')).pack(side='left',fill='x',expand=True,padx=(4,0))

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

    def _refresh_thread_list(self):
        if not hasattr(self,'thread_list'): return
        self.thread_list.delete(0,'end')
        for i,c in enumerate(self.thread_palette): self.thread_list.insert('end',f'{i+1}. {c.upper()}')
        if self.thread_palette: self.thread_list.selection_set(0)

    def add_thread_color(self):
        chosen=colorchooser.askcolor(title='Choose thread color')[1]
        if chosen:
            self.thread_palette.append(chosen); self._refresh_thread_list(); self.status.set(f'Thread color added: {chosen}')

    def edit_thread_color(self):
        sel=self.thread_list.curselection()
        if not sel: messagebox.showinfo('Select color','Select a thread color first.'); return
        idx=sel[0]; chosen=colorchooser.askcolor(color=self.thread_palette[idx],title='Edit thread color')[1]
        if chosen: self.thread_palette[idx]=chosen; self._refresh_thread_list(); self.thread_list.selection_set(idx)

    def remove_thread_color(self):
        sel=self.thread_list.curselection()
        if not sel: messagebox.showinfo('Select color','Select a thread color first.'); return
        if len(self.thread_palette)<=1: messagebox.showwarning('Keep one color','At least one thread color is required.'); return
        del self.thread_palette[sel[0]]; self.region_mappings=[m for m in self.region_mappings if m['thread_index']!=sel[0]];
        for m in self.region_mappings:
            if m['thread_index']>sel[0]: m['thread_index']-=1
        self._refresh_thread_list(); self._refresh_mapping_list()

    def enable_sample(self):
        if self.image is None:
            messagebox.showinfo('Open image','Open an image and show the original or embroidery preview first.'); return
        self.sample_mode=True
        self.status.set('Color sampling enabled: click the image area in the preview to sample a source color.')

    def _sample_canvas_color(self,event):
        if not getattr(self,'sample_mode',False) or self.image is None or self.preview_base is None: return
        try:
            cx=self.canvas.canvasx(event.x); cy=self.canvas.canvasy(event.y)
            ix=int(cx/max(self.zoom,0.01)); iy=int(cy/max(self.zoom,0.01))
            if ix<0 or iy<0 or ix>=self.preview_base.width or iy>=self.preview_base.height: return
            # Sample from the original image at proportional coordinates, independent of preview type.
            ox=min(self.image.width-1,int(ix*self.image.width/self.preview_base.width)); oy=min(self.image.height-1,int(iy*self.image.height/self.preview_base.height))
            self.sampled_rgb=self.image.convert('RGB').getpixel((ox,oy)); self.sample_mode=False
            self.status.set(f'Sampled source color RGB {self.sampled_rgb}. Select a thread color and click Assign Thread.')
        except Exception as e:
            self.sample_mode=False; self.status.set('Color sample failed: '+str(e))

    def assign_region_thread(self):
        if self.sampled_rgb is None:
            messagebox.showinfo('Sample a region','Click Sample from Preview, then click the image to sample a color.'); return
        sel=self.thread_list.curselection()
        if not sel:
            messagebox.showinfo('Select thread','Select a thread color in Thread Color Management first.'); return
        idx=sel[0]; rgb=self.sampled_rgb; thread=self.thread_palette[idx]
        # Replace existing mapping for the same sampled source color.
        self.region_mappings=[m for m in self.region_mappings if m['rgb']!=rgb]
        self.region_mappings.append({'rgb':rgb,'thread_index':idx,'thread':thread})
        self._refresh_mapping_list(); self.status.set(f'Source RGB {rgb} mapped to thread {thread}.')

    def _refresh_mapping_list(self):
        if not hasattr(self,'mapping_list'): return
        self.mapping_list.delete(0,'end')
        for m in self.region_mappings:
            self.mapping_list.insert('end',f"RGB {m['rgb']} → {m['thread']} (thread #{m['thread_index']+1})")
        if self.region_mappings: self.mapping_list.selection_set('end')

    def remove_region_map(self):
        sel=self.mapping_list.curselection()
        if not sel: return
        del self.region_mappings[sel[0]]; self._refresh_mapping_list(); self.status.set('Region mapping removed.')

    def _thread_for_pixel(self, col, palette):
        if self.region_mappings:
            # Match the closest sampled source color; if it is close enough, use its assigned thread.
            nearest=min(self.region_mappings,key=lambda m:sum((col[k]-m['rgb'][k])**2 for k in range(3)))
            dist=sum((col[k]-nearest['rgb'][k])**2 for k in range(3))
            if dist <= 65**2*3 and 0 <= nearest['thread_index'] < len(palette): return nearest['thread_index']
        return min(range(len(palette)),key=lambda i:sum((col[k]-palette[i][k])**2 for k in range(3)))

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
        im=self.image.copy(); im.thumbnail((850,700),Image.Resampling.LANCZOS); rgba=im.convert('RGBA'); rgb=rgba.convert('RGB')
        # Approximate thread simulation: quantize pixels to chosen thread palette, then draw short slanted thread strokes.
        palette=[]
        for hx in self.thread_palette:
            try: palette.append(tuple(int(hx[i:i+2],16) for i in (1,3,5)))
            except Exception: pass
        if not palette: palette=[(32,32,32)]
        pix=rgb.load(); out=Image.new('RGBA',rgba.size,(238,232,218,255)); d=ImageDraw.Draw(out)
        step=max(2,int(self.stitch_spacing.get()*4)); length=max(2,int(self.stitch_length.get()*1.5)); threshold=int(255*self.emb_threshold.get()/100)
        for y in range(1,rgba.height-1,step):
            reverse=((y//step)%2)==1
            for x in (range(1,rgba.width-1,length) if not reverse else range(rgba.width-2,0,-length)):
                col=pix[x,y]; lum=int(.2126*col[0]+.7152*col[1]+.0722*col[2])
                if lum>=threshold: continue
                nearest=palette[self._thread_for_pixel(col,palette)]
                x2=max(1,min(rgba.width-2,x+(-length if reverse else length)))
                d.line((x,y,x2,min(rgba.height-2,y+max(1,step//2))),fill=nearest+(255,),width=max(1,min(3,int(self.stitch_spacing.get()))))
        return out

    def embroidery_preview(self):
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return
        self.tabs.select(1); self._set_preview(self.make_embroidery_preview(),'embroidery'); self.fit_view()
        self.status.set('Thread-color embroidery-style preview ready. Visual simulation only; inspect machine file separately.')

    def build_pattern(self):
        try:
            from pyembroidery import EmbPattern, STITCH, JUMP, COLOR_CHANGE, END
        except ImportError:
            messagebox.showerror('Embroidery dependency missing','pyembroidery is not installed. Rebuild the EXE from the updated GitHub workflow.'); return None
        if self.image is None:messagebox.showinfo('Open image','Please open an image first.');return None
        if not self.thread_palette: messagebox.showwarning('No thread colors','Add at least one thread color.'); return None
        # Multi-color raster stitch approximation. This is NOT professional object-based digitizing.
        src=self.image.copy().convert('RGB'); target_w=max(20,min(250,int(self.emb_width.get())))
        target_h=max(1,round(target_w*src.height/src.width)); pxw=max(1,int(target_w*2)); pxh=max(1,int(target_h*2))
        src=src.resize((pxw,pxh),Image.Resampling.LANCZOS); gray=ImageOps.grayscale(src); g=gray.load(); colorpx=src.load(); w,h=gray.size
        palette=[]
        for hx in self.thread_palette:
            palette.append(tuple(int(hx[i:i+2],16) for i in (1,3,5)))
        pattern=EmbPattern(); pattern.set_metadata('name',os.path.basename(self.path)[:16] or 'DTF Embroidery')
        # pyembroidery coordinates use 0.1 mm units; scale pixels to approximate design mm.
        scale=5.0; row_px=max(1,int(self.stitch_spacing.get()*2)); step=max(1,int(self.stitch_length.get()*2)); threshold=int(255*self.emb_threshold.get()/100)
        if self.stitch_type.get() == 'Running Stitch': step=max(1,int(self.stitch_length.get()))
        max_stitches=50000; count=0; current_color=None
        for yi,y in enumerate(range(0,h,row_px)):
            xs=list(range(0,w,step))
            if yi%2: xs.reverse()
            row=[]
            for x in xs:
                if g[x,y]>=threshold: continue
                col=colorpx[x,y]; nearest=self._thread_for_pixel(col,palette)
                
                stitch_y=y/2*scale
                if self.stitch_type.get().startswith('Satin-like'):
                    stitch_y += (1.0 if (x//step)%2 else -1.0) * min(2.0,self.stitch_spacing.get())
                row.append((x/2*scale,stitch_y,nearest))
            # Split into adjacent runs of the same thread color.
            runs=[]; run=[]; prev=None
            for point in row:
                if prev is not None and (abs(point[0]-prev[0])>self.stitch_length.get()*10 or point[2]!=prev[2]):
                    if run:runs.append(run)
                    run=[]
                run.append(point); prev=point
            if run:runs.append(run)
            for run in runs:
                if not run: continue
                colidx=run[0][2]
                if current_color is None:
                    pattern.add_thread({'color':palette[colidx],'description':self.thread_palette[colidx]})
                    current_color=colidx
                elif colidx!=current_color:
                    pattern.add_stitch_absolute(COLOR_CHANGE,run[0][0],run[0][1]); pattern.add_thread({'color':palette[colidx],'description':self.thread_palette[colidx]}); current_color=colidx
                x0,y0,_=run[0]; pattern.add_stitch_absolute(JUMP,x0,y0)
                if self.underlay.get() and len(run)>3:
                    # one simple offset pass; not a real professional underlay
                    pattern.add_stitch_absolute(STITCH,x0,y0+1.5); count+=1
                for x,y1,_ in run[1:]:
                    pattern.add_stitch_absolute(STITCH,x,y1); count+=1
                    if count>=max_stitches: break
                if count>=max_stitches: break
            if count>=max_stitches: break
        pattern.add_stitch_absolute(END,0,0)
        if count<20: messagebox.showwarning('Few stitches','Very few stitches generated. Lower darkness threshold or use a darker image.')
        self.status.set(f'Approximate multi-color path generated: {count:,} stitches. Verify size, trims and color changes in embroidery software.')
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
        self.emb_width.set(100);self.stitch_spacing.set(1.5);self.emb_threshold.set(55);self.stitch_length.set(3.0);self.stitch_type.set('Fill / Tatami (approx.)');self.underlay.set(True);self.thread_palette=['#202020','#D62828','#2474D2','#F2C230','#FFFFFF'];self._refresh_thread_list();self.status.set('Embroidery settings reset.')
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
