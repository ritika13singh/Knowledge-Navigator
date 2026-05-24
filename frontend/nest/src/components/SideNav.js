import React from 'react';
import {
  HiOutlinePlus,
  HiOutlineChatAlt2,
  HiOutlineDocumentText,
  HiOutlineLightBulb,
  HiOutlineStar,
  HiOutlineCollection,
  HiOutlineFolder,
} from 'react-icons/hi';
import AppLogo from './AppLogo';

const HISTORY_ICONS = [
  HiOutlineStar,
  HiOutlineChatAlt2,
  HiOutlineDocumentText,
  HiOutlineLightBulb,
  HiOutlineCollection,
  HiOutlineFolder,
  HiOutlineChatAlt2,
  HiOutlineDocumentText,
];

function SideNav({ chats = [], activeChatId, onNewChat, onSelectChat, open = true, onClose }) {
  return (
    <>
      {open && (
        <button
          type="button"
          className="side-nav__backdrop"
          aria-label="Close sidebar"
          onClick={onClose}
          tabIndex={-1}
        />
      )}
      <aside
        className={`side-nav ${open ? 'side-nav--open' : ''}`}
        role="navigation"
        aria-label="Chat history"
      >
        <div className="side-nav__brand">
          <AppLogo size="small" />
        </div>
        <button
          type="button"
          className="side-nav__new-chat"
          onClick={onNewChat}
          aria-label="Start new chat"
        >
          <HiOutlinePlus className="side-nav__new-chat-icon" aria-hidden="true" />
          <span>New chat</span>
        </button>

        <div className="side-nav__history">
          <div className="side-nav__history-label">Chat history</div>
          <ul className="side-nav__list">
            {chats.length === 0 && (
              <li className="side-nav__empty">No chats yet</li>
            )}
            {chats.map((chat, index) => {
              const IconComponent = HISTORY_ICONS[index % HISTORY_ICONS.length];
              return (
                <li key={chat.id}>
                  <button
                    type="button"
                    className={`side-nav__item ${activeChatId === chat.id ? 'side-nav__item--active' : ''}`}
                    onClick={() => onSelectChat(chat.id)}
                    aria-current={activeChatId === chat.id ? 'true' : undefined}
                  >
                    <IconComponent className="side-nav__item-icon" aria-hidden="true" />
                    <span className="side-nav__item-title">{chat.title || 'New chat'}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </aside>
    </>
  );
}

export default SideNav;
