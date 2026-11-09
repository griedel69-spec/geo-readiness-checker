A modal confirmation dialog with dimmed overlay.

```jsx
<Dialog open={open} title="Angebot löschen?" onClose={close} actions={<><Button variant="secondary" onClick={close}>Abbrechen</Button><Button variant="primary" onClick={confirm}>Löschen</Button></>}>
  Diese Aktion kann nicht rückgängig gemacht werden.
</Dialog>
```
