import React from 'react';
export function Tag({children,onRemove}){
  return <span className={`gr-tag${onRemove?' gr-tag-removable':''}`}>{children}{onRemove&&<button onClick={onRemove} aria-label="entfernen">✕</button>}</span>;
}
