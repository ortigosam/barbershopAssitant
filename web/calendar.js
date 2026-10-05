const $ = id => document.getElementById(id);
const days = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
let token = '', bookings = [], settings = null, selectedBooking = null, requestId = null, firstMinute = 540, availableByDate = new Map();
function madridToday(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
function localDate(value){return new Date(value+'T12:00:00');}
function iso(date){return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');}
function shift(date,n){const value=new Date(date);value.setDate(value.getDate()+n);return value;}
function monday(date){return shift(date,-((date.getDay()+6)%7));}
let week=monday(localDate(madridToday()));
async function api(path, options={}){
 const r=await fetch(path,{...options,headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json',...options.headers}});
 if(r.status===204)return null;
 const data=await r.json();
 if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Revisa los datos introducidos.');
 return data;
}
function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
function dateLabel(value){return localDate(value).toLocaleDateString('es-ES',{weekday:'long',day:'numeric',month:'long'});}
async function availableBookingSlots(count){
 const [current,next]=await Promise.all([
  api('/admin/availability?'+new URLSearchParams({week:'current',count})),
  api('/admin/availability?'+new URLSearchParams({week:'next',count}))
 ]);
 return [...current.slots,...next.slots];
}
function fillTimeOptions(byDate,date,preferred){
 const select=$('appointment-form').elements.time;select.replaceChildren();
 for(const slot of byDate.get(date)??[]){
  const option=new Option(slot.slice(11,16),slot.slice(11,16));select.append(option);
 }
 if(preferred && [...select.options].some(option=>option.value===preferred))select.value=preferred;
 if(!select.value && select.options.length)select.selectedIndex=0;
}
async function fillBookingChoices(preferredDate=null,preferredTime=null){
 const count=Number($('appointment-form').elements.count.value||1);
 const slots=await availableBookingSlots(count);
 const byDate=new Map();
 for(const slot of slots){const date=slot.timestamp.slice(0,10);if(!byDate.has(date))byDate.set(date,[]);byDate.get(date).push(slot.timestamp);}
 availableByDate=byDate;
 const dateSelect=$('appointment-form').elements.date;
 const dates=[...byDate.keys()];
 dateSelect.min=dates[0]??'';dateSelect.max=dates.at(-1)??'';
 dateSelect.dataset.availableDates=dates.join(',');
 const date=preferredDate&&byDate.has(preferredDate)?preferredDate:dates[0];
 dateSelect.value=date??'';
 fillTimeOptions(byDate,date,preferredTime);
 return slots.length;
}
async function refresh(){
 try {
  [bookings,settings]=await Promise.all([api('/admin/bookings?'+new URLSearchParams({start:iso(week)+'T00:00:00',end:iso(shift(week,7))+'T00:00:00'})),api('/admin/settings')]);
  render();$('notice').textContent='';$('updated').textContent='Actualizado '+new Date().toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'});
 }catch(e){$('notice').textContent=e.message;}
}
function minutes(time){const [h,m]=time.split(':').map(Number);return h*60+m;}
function position(time){return (minutes(time)-firstMinute)*1.2;}
function render(){
 $('total').textContent=bookings.length+' citas';
 $('week-title').textContent=week.toLocaleDateString('es-ES',{day:'numeric',month:'long'})+' — '+shift(week,6).toLocaleDateString('es-ES',{day:'numeric',month:'long',year:'numeric'});
 const root=$('calendar');root.replaceChildren();const heads=el('div',undefined,'day-heads');heads.append(el('div'));const body=el('div',undefined,'calendar-body');
 const windows=Array.from({length:7},(_,i)=>settings.exceptions[iso(shift(week,i))]??settings.weekly[String(i)]??[]).flat();
 firstMinute=Math.floor(Math.min(540,...windows.map(w=>minutes(w[0])),...bookings.map(b=>minutes(b.timestamp.slice(11,16))))/60)*60;
 const lastMinute=Math.ceil(Math.max(1320,...windows.map(w=>minutes(w[1])),...bookings.map(b=>minutes(b.end.slice(11,16))))/60)*60;
 body.style.height=(lastMinute-firstMinute)*1.2+'px';
 const ruler=el('div',undefined,'ruler');for(let m=firstMinute;m<lastMinute;m+=60){const label=el('span',String(m/60).padStart(2,'0')+':00','hour');label.style.top=(m-firstMinute)*1.2+'px';ruler.append(label);}body.append(ruler);
 for(let i=0;i<7;i++){
  const date=iso(shift(week,i));const head=el('div',undefined,'day-head'+(date===madridToday()?' today':''));head.append(el('span',days[i]),el('strong',String(shift(week,i).getDate())));heads.append(head);
  const column=el('div',undefined,'day');
  for(const [start,end] of settings.exceptions[date]??settings.weekly[String(i)]??[]){const open=el('div',undefined,'open-window');open.style.top=position(start)+'px';open.style.height=(minutes(end)-minutes(start))*1.2+'px';column.append(open);}
  column.onclick=e=>{if(e.target!==column)return;const mins=Math.floor((e.clientY-column.getBoundingClientRect().top)/24)*20+firstMinute;openAppointment(null,date,String(Math.floor(mins/60)).padStart(2,'0')+':'+String(mins%60).padStart(2,'0'));};
  for(const b of bookings.filter(b=>b.timestamp.slice(0,10)===date)){
   const button=el('button',b.timestamp.slice(11,16)+' · '+b.name,'appointment '+b.status);button.style.top=position(b.timestamp.slice(11,16))+'px';button.style.height='24px';
   button.title=b.name+' · '+b.telephone+' · '+b.timestamp.slice(11,16);button.onclick=()=>openBooking(b);column.append(button);
  }body.append(column);
 }root.append(heads,body);
}
$('login-form').onsubmit=async e=>{
 e.preventDefault();token=$('token').value.trim();$('login-error').textContent='';
 try{settings=await api('/admin/settings');$('login').hidden=true;$('workspace').hidden=false;$('connected').hidden=false;$('token').value='';await refresh();}
 catch(error){$('login-error').textContent=error.message;token='';}
};
$('logout').onclick=()=>{token='';bookings=[];$('calendar').replaceChildren();$('workspace').hidden=true;$('connected').hidden=true;$('login').hidden=false;};
$('previous').onclick=()=>{week=shift(week,-7);refresh();};$('next').onclick=()=>{week=shift(week,7);refresh();};$('today').onclick=()=>{week=monday(localDate(madridToday()));refresh();};$('refresh').onclick=refresh;
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
function openAppointment(date=madridToday(),time='10:00'){
 selectedBooking=null;requestId=crypto.randomUUID();const form=$('appointment-form');form.reset();$('appointment-error').textContent='';
 $('appointment-title').textContent='Nueva cita';$('appointment-status').textContent='';
 $('customer-fields').hidden=false;$('appointment-fields').hidden=false;$('booking-details').hidden=true;
 [...$('appointment-fields').querySelectorAll('input, select')].forEach(field=>field.disabled=false);
 form.elements.name.required=true;form.elements.telephone.required=true;
 form.elements.date.disabled=true;form.elements.time.disabled=true;
 $('cancel-booking').hidden=true;$('save-booking').hidden=false;$('save-booking').disabled=true;$('appointment-dialog').showModal();
 fillBookingChoices(date,time).then(total=>{
  if(!total){$('appointment-error').textContent='No hay huecos disponibles esta semana ni la siguiente.';return;}
  form.elements.date.disabled=false;form.elements.time.disabled=false;
  $('save-booking').disabled=false;
 }).catch(error=>{$('appointment-error').textContent=error.message;});
}
function openBooking(booking){
 selectedBooking=booking;const form=$('appointment-form');form.reset();$('appointment-error').textContent='';
 $('appointment-title').textContent='Cita';$('appointment-status').textContent=booking.name+' · '+booking.telephone;
 $('customer-fields').hidden=true;$('appointment-fields').hidden=true;$('booking-details').hidden=false;
 [...$('appointment-fields').querySelectorAll('input, select')].forEach(field=>field.disabled=true);
 $('booking-details').textContent=booking.timestamp.slice(0,16).replace('T',' a las ')+' · '+(booking.status==='completed'?'Completada':'Confirmada');
 const started=booking.timestamp<=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date()).replace(' ','T');
 $('cancel-booking').hidden=!!started;$('save-booking').hidden=true;$('appointment-dialog').showModal();
}
$('new').onclick=()=>openAppointment();
const dateField=$('appointment-form').elements.date;
dateField.addEventListener('click',()=>{
 if(typeof dateField.showPicker==='function'){
  try{dateField.showPicker();}catch(_error){/* el navegador ya tiene el selector abierto */}
 }
});
dateField.addEventListener('keydown',event=>{
 if(!['Tab','Escape','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))event.preventDefault();
});
$('appointment-form').elements.date.onchange=()=>{
 const date=$('appointment-form').elements.date.value;
 const time=$('appointment-form').elements.time;
 if(!availableByDate.has(date)){
  time.replaceChildren();$('save-booking').disabled=true;
  $('appointment-error').textContent='Ese día no tiene huecos disponibles.';
  return;
 }
 fillTimeOptions(availableByDate,date,time.value);$('appointment-error').textContent='';
 $('save-booking').disabled=!time.value;
};
$('appointment-form').elements.count.onchange=()=>{
 const date=$('appointment-form').elements.date.value;const time=$('appointment-form').elements.time.value;
 $('save-booking').disabled=true;
 fillBookingChoices(date,time).then(total=>{$('save-booking').disabled=!total;}).catch(error=>{$('appointment-error').textContent=error.message;});
};
$('appointment-form').oninput=()=>{requestId=crypto.randomUUID();};
$('appointment-form').onsubmit=async e=>{
 e.preventDefault();const f=e.target.elements;const timestamp=f.date.value+'T'+f.time.value+':00';$('save-booking').disabled=true;
 try{
  const digits=f.telephone.value.replace(/\D/g,'');
  const prefix=f['country-code'].value;
  const countryDigits=prefix.slice(1);
  const raw=f.telephone.value.trim();
  const international=raw.startsWith('+')||raw.startsWith('00');
  const normalized=raw.startsWith('00')?digits.slice(2):digits;
  const local=international&&normalized.startsWith(countryDigits)?normalized.slice(countryDigits.length):digits;
  const payload={timestamp,name:f.name.value,telephone:prefix+local,count:Number(f.count.value),request_id:requestId};
  await api('/admin/bookings',{method:'POST',body:JSON.stringify(payload)});
  $('appointment-dialog').close();await refresh();$('notice').textContent='Cita guardada correctamente.';
 }catch(error){$('appointment-error').textContent=error.message;}finally{$('save-booking').disabled=false;}
};
$('cancel-booking').onclick=async()=>{
 if(!confirm('¿Cancelar esta cita y liberar su horario?'))return;
 try{await api('/admin/bookings/'+selectedBooking.id,{method:'DELETE'});$('appointment-dialog').close();await refresh();$('notice').textContent='Cita cancelada. El horario vuelve a estar disponible.';}
 catch(error){$('appointment-error').textContent=error.message;}
};
function scheduleRow(label,windows,exception=false){
 const row=el('div',undefined,'schedule-row'+(exception?' exception-row':''));let title;
 if(exception){title=el('input');title.type='date';title.value=label;title.required=true;}else{title=el('span',label);}
 row.append(title);
 for(let n=0;n<4;n++){const input=el('input');input.type='time';input.setAttribute('aria-label',(exception?'Fecha especial':label)+' '+['inicio mañana','fin mañana','inicio tarde','fin tarde'][n]);input.value=windows[Math.floor(n/2)]?.[n%2]??'';row.append(input);}
 if(exception){const remove=el('button','×');remove.type='button';remove.onclick=()=>row.remove();row.append(remove);}
 return row;
}
$('settings').onclick=()=>{
 $('weekly-editor').replaceChildren(...days.map((d,i)=>scheduleRow(d,settings.weekly[i]??[])));
 $('exceptions-editor').replaceChildren(...Object.entries(settings.exceptions).sort().map(([d,w])=>scheduleRow(d,w,true)));
 $('settings-error').textContent='';$('settings-dialog').showModal();
};
$('add-exception').onclick=()=>$('exceptions-editor').append(scheduleRow('',[],true));
function readWindows(row){
 const values=[...row.querySelectorAll('input[type=time]')].map(i=>i.value);const windows=[];
 for(let i=0;i<4;i+=2){if(!values[i]&&!values[i+1])continue;if(!values[i]||!values[i+1])throw new Error('Completa el inicio y el fin de cada intervalo.');windows.push([values[i],values[i+1]]);}return windows;
}
$('settings-form').onsubmit=async e=>{
 e.preventDefault();
 try{
  const weekly=Object.fromEntries([...$('weekly-editor').children].map((r,i)=>[String(i),readWindows(r)]));const exceptions={};
  for(const row of $('exceptions-editor').children){const day=row.querySelector('input[type=date]').value;if(day in exceptions)throw new Error('Hay una fecha especial repetida.');exceptions[day]=readWindows(row);}
  settings=await api('/admin/settings',{method:'PUT',body:JSON.stringify({weekly,exceptions,version:settings.version})});
  $('settings-dialog').close();await refresh();$('notice').textContent='Horario actualizado.';
 }catch(error){$('settings-error').textContent=error.message;}
};
setInterval(()=>{if(token&&!document.querySelector('dialog[open]'))refresh();},60000);
