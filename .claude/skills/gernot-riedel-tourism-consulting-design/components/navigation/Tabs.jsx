import React from 'react';
export function Tabs({tabs=[],active,onChange}){
  return <div className="gr-tabs">
    {tabs.map(t=><button key={t} className={`gr-tab${t===active?' gr-tab-active':''}`} onClick={()=>onChange&&onChange(t)}>{t}</button>)}
  </div>;
}
