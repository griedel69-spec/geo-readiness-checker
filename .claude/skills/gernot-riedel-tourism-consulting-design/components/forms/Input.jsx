import React from 'react';
export function Input({label,placeholder,value,onChange,disabled=false,error,help,type='text'}){
  return <div className="gr-field">
    {label&&<label className="gr-label">{label}</label>}
    <input className="gr-input" type={type} placeholder={placeholder} value={value} onChange={onChange} disabled={disabled}/>
    {error?<span className="gr-help gr-help-error">{error}</span>:help?<span className="gr-help">{help}</span>:null}
  </div>;
}
