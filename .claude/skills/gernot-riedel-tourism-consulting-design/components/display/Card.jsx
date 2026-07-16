import React from 'react';
export function Card({title,children}){
  return <div className="gr-card">
    {title&&<h3 className="gr-card-title">{title}</h3>}
    <div className="gr-card-body">{children}</div>
  </div>;
}
