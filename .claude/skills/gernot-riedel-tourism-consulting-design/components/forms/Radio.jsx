import React from 'react';
export function Radio({label,name,checked,onChange,disabled=false}){
  return <label className="gr-radio-row">
    <input type="radio" className="gr-radio" name={name} checked={checked} onChange={onChange} disabled={disabled}/>
    {label}
  </label>;
}
