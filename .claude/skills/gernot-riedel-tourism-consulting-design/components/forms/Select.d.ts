export interface SelectOption{label?:string;value?:string;}
export interface SelectProps{
  label?:string;
  options?:(SelectOption|string)[];
  value?:string;
  onChange?:(e:React.ChangeEvent<HTMLSelectElement>)=>void;
  disabled?:boolean;
}
export function Select(props:SelectProps):JSX.Element;
