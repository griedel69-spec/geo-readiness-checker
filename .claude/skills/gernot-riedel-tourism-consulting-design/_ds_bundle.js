/* @ds-bundle: {"format":4,"namespace":"GernotRiedelTourismConsultingDesignSystem_02866a","components":[{"name":"Badge","sourcePath":"components/display/Badge.jsx"},{"name":"Card","sourcePath":"components/display/Card.jsx"},{"name":"Tag","sourcePath":"components/display/Tag.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/feedback/Tooltip.jsx"},{"name":"Button","sourcePath":"components/forms/Button.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"IconButton","sourcePath":"components/forms/IconButton.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"}],"sourceHashes":{"components/display/Badge.jsx":"4a0758561fd7","components/display/Card.jsx":"f09716c4e095","components/display/Tag.jsx":"d00658db4945","components/feedback/Dialog.jsx":"1ddf31b0e3c1","components/feedback/Toast.jsx":"f50a8d4649ba","components/feedback/Tooltip.jsx":"ec8559ff68cb","components/forms/Button.jsx":"07c65821f4d3","components/forms/Checkbox.jsx":"6ecaaa9ccdcf","components/forms/IconButton.jsx":"6982a6e8fefc","components/forms/Input.jsx":"11f4ec22be1e","components/forms/Radio.jsx":"6ccfdc071f1e","components/forms/Select.jsx":"7cccc4ce3c5e","components/forms/Switch.jsx":"fd60783c4f04","components/navigation/Tabs.jsx":"51bdc8711661"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.GernotRiedelTourismConsultingDesignSystem_02866a = window.GernotRiedelTourismConsultingDesignSystem_02866a || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/display/Badge.jsx
try { (() => {
function Badge({
  variant = 'brand',
  children
}) {
  return /*#__PURE__*/React.createElement("span", {
    className: `gr-badge gr-badge-${variant}`
  }, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Badge.jsx", error: String((e && e.message) || e) }); }

// components/display/Card.jsx
try { (() => {
function Card({
  title,
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "gr-card"
  }, title && /*#__PURE__*/React.createElement("h3", {
    className: "gr-card-title"
  }, title), /*#__PURE__*/React.createElement("div", {
    className: "gr-card-body"
  }, children));
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Card.jsx", error: String((e && e.message) || e) }); }

// components/display/Tag.jsx
try { (() => {
function Tag({
  children,
  onRemove
}) {
  return /*#__PURE__*/React.createElement("span", {
    className: `gr-tag${onRemove ? ' gr-tag-removable' : ''}`
  }, children, onRemove && /*#__PURE__*/React.createElement("button", {
    onClick: onRemove,
    "aria-label": "entfernen"
  }, "\u2715"));
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/display/Tag.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
function Dialog({
  open,
  title,
  children,
  onClose,
  actions
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "gr-dialog-overlay",
    onClick: onClose
  }, /*#__PURE__*/React.createElement("div", {
    className: "gr-dialog",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("h3", {
    className: "gr-dialog-title"
  }, title), /*#__PURE__*/React.createElement("p", {
    className: "gr-dialog-body"
  }, children), /*#__PURE__*/React.createElement("div", {
    className: "gr-dialog-actions"
  }, actions)));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
function Toast({
  children,
  accent = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: `gr-toast${accent ? ' gr-toast-accent' : ''}`
  }, children);
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tooltip.jsx
try { (() => {
function Tooltip({
  label,
  children
}) {
  return /*#__PURE__*/React.createElement("span", {
    className: "gr-tooltip-wrap"
  }, children, /*#__PURE__*/React.createElement("span", {
    className: "gr-tooltip"
  }, label));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/forms/Button.jsx
try { (() => {
function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  children,
  onClick,
  type = 'button'
}) {
  const sizeClass = size === 'sm' ? ' gr-btn-sm' : size === 'lg' ? ' gr-btn-lg' : '';
  return /*#__PURE__*/React.createElement("button", {
    type: type,
    disabled: disabled,
    onClick: onClick,
    className: `gr-btn gr-btn-${variant}${sizeClass}`
  }, children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Button.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function Checkbox({
  label,
  checked,
  onChange,
  disabled = false
}) {
  return /*#__PURE__*/React.createElement("label", {
    className: "gr-check-row"
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    className: "gr-check",
    checked: checked,
    onChange: onChange,
    disabled: disabled
  }), label);
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/IconButton.jsx
try { (() => {
function IconButton({
  children,
  onClick,
  disabled = false,
  label
}) {
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    "aria-label": label,
    disabled: disabled,
    onClick: onClick,
    className: "gr-iconbtn"
  }, children);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function Input({
  label,
  placeholder,
  value,
  onChange,
  disabled = false,
  error,
  help,
  type = 'text'
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "gr-field"
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "gr-label"
  }, label), /*#__PURE__*/React.createElement("input", {
    className: "gr-input",
    type: type,
    placeholder: placeholder,
    value: value,
    onChange: onChange,
    disabled: disabled
  }), error ? /*#__PURE__*/React.createElement("span", {
    className: "gr-help gr-help-error"
  }, error) : help ? /*#__PURE__*/React.createElement("span", {
    className: "gr-help"
  }, help) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
function Radio({
  label,
  name,
  checked,
  onChange,
  disabled = false
}) {
  return /*#__PURE__*/React.createElement("label", {
    className: "gr-radio-row"
  }, /*#__PURE__*/React.createElement("input", {
    type: "radio",
    className: "gr-radio",
    name: name,
    checked: checked,
    onChange: onChange,
    disabled: disabled
  }), label);
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function Select({
  label,
  options = [],
  value,
  onChange,
  disabled = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "gr-field"
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "gr-label"
  }, label), /*#__PURE__*/React.createElement("select", {
    className: "gr-select",
    value: value,
    onChange: onChange,
    disabled: disabled
  }, options.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value || o,
    value: o.value || o
  }, o.label || o))));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function Switch({
  checked,
  onChange,
  disabled = false,
  label
}) {
  return /*#__PURE__*/React.createElement("label", {
    className: "gr-switch",
    "aria-label": label
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: checked,
    onChange: onChange,
    disabled: disabled
  }), /*#__PURE__*/React.createElement("span", {
    className: "gr-switch-track"
  }), /*#__PURE__*/React.createElement("span", {
    className: "gr-switch-thumb"
  }));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function Tabs({
  tabs = [],
  active,
  onChange
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "gr-tabs"
  }, tabs.map(t => /*#__PURE__*/React.createElement("button", {
    key: t,
    className: `gr-tab${t === active ? ' gr-tab-active' : ''}`,
    onClick: () => onChange && onChange(t)
  }, t)));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Tabs = __ds_scope.Tabs;

})();
