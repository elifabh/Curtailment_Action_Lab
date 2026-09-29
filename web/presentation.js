/* Local PDF handoff. A selected file stays in this tab; nothing is uploaded. */
(()=>{'use strict';
const $=id=>document.getElementById(id),old=$('presentation-open');
old.textContent='Result walkthrough';
const open=document.createElement('button');open.id='pitch-open';open.type='button';open.className='button button-primary compact';open.textContent='Presentation';old.after(open);
const panel=document.createElement('section');panel.className='panel presentation-tools';panel.id='presentation-tools';
panel.innerHTML='<h2>Your presentation</h2><p>The Presentation button opens the current English PDF. Choose a PDF designed elsewhere to use it in this browser tab. No upload is made.</p><label for="presentation-file">Use your own PDF</label><input id="presentation-file" type="file" accept="application/pdf,.pdf"><p id="presentation-file-status" class="quiet-note" aria-live="polite">Included: the current v5 draft. The Result walkthrough button shows the selected calculation.</p><a id="presentation-link" class="text-button" target="_blank" rel="noopener">Open or save the current PDF ↗</a>';
$('overview').append(panel);let chosen=null,embedded=null;
function current(){if(chosen)return chosen;if(window.ACTIONLAB_DATA){if(!embedded){const bytes=Uint8Array.from(atob(window.ACTIONLAB_DATA.presentation_pdf_base64),c=>c.charCodeAt(0));embedded=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));}return embedded;}return '/presentation/Pitch_EN.pdf';}
function ready(){try{$('presentation-link').href=current();open.disabled=false;}catch(e){open.disabled=true;$('presentation-file-status').textContent='The PDF could not be loaded. Choose a local PDF below.';}}
open.onclick=()=>{const url=current();$('presentation-link').href=url;window.open(url,'_blank','noopener');};
$('presentation-file').addEventListener('change',()=>{const file=$('presentation-file').files[0];if(!file)return;if(file.size>20*1024*1024){$('presentation-file-status').textContent='Choose a PDF of 20 MB or less.';return;}const r=new FileReader();r.onload=()=>{const a=new Uint8Array(r.result);if(String.fromCharCode(...a.slice(0,5))!=='%PDF-'){$('presentation-file-status').textContent='That file is not a PDF. The previous presentation remains selected.';return;}if(chosen)URL.revokeObjectURL(chosen);chosen=URL.createObjectURL(new Blob([a],{type:'application/pdf'}));$('presentation-file-status').textContent='Selected: '+file.name+'. This selection lasts for this browser tab only. To include it permanently, replace presentation/Pitch_EN.pdf and rebuild the offline page.';ready();};r.onerror=()=>{$('presentation-file-status').textContent='The PDF could not be read. The previous presentation remains selected.';};r.readAsArrayBuffer(file);});
ready();
})();
