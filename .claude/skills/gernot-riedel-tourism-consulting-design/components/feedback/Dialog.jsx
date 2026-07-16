import React from 'react';
export function Dialog({open,title,children,onClose,actions}){
  if(!open) return null;
  return <div className="gr-dialog-overlay" onClick={onClose}>
    <div className="gr-dialog" onClick={e=>e.stopPropagation()}>
      <h3 className="gr-dialog-title">{title}</h3>
      <p className="gr-dialog-body">{children}</p>
      <div className="gr-dialog-actions">{actions}</div>
    </div>
  </div>;
}
