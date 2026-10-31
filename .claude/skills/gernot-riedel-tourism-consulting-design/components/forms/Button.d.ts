export interface ButtonProps{
  variant?:'primary'|'accent'|'secondary'|'ghost';
  size?:'sm'|'md'|'lg';
  disabled?:boolean;
  children:React.ReactNode;
  onClick?:()=>void;
  type?:'button'|'submit';
}
export function Button(props:ButtonProps):JSX.Element;
