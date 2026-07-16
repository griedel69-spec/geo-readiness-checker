export interface RadioProps{
  label:React.ReactNode;
  name:string;
  checked?:boolean;
  onChange?:(e:React.ChangeEvent<HTMLInputElement>)=>void;
  disabled?:boolean;
}
export function Radio(props:RadioProps):JSX.Element;
