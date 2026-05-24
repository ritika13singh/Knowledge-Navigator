import React, { useState, useRef, useEffect } from 'react';
import { HiOutlinePaperAirplane } from 'react-icons/hi';
function ChatInput({ onSend, disabled, placeholder }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, [value]);

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <div className="chat-input__wrap">
        <textarea
          ref={textareaRef}
          className="chat-input__field"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Message NESst...'}
          rows={1}
          disabled={disabled}
          aria-label="Message input"
          maxLength={10000}
        />
        <button
          type="submit"
          className="chat-input__submit"
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <HiOutlinePaperAirplane className="chat-input__submit-icon" aria-hidden="true" />
        </button>
      </div>
    </form>
  );
}

export default ChatInput;
