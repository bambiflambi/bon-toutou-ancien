/* Freemarket — icônes (traits simples, dessinées pour Freemarket). */
const G=d=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const IC={
 inbox:G('<path d="M3 13l3-8h12l3 8v6H3z"/><path d="M3 13h5l1 2h6l1-2h5"/>'),
 folder:G('<path d="M3 6h7l2 2h9v11H3z"/>'),
 id:G('<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="11" r="2.5"/><path d="M5.5 16c.8-1.5 2-2 3.5-2s2.7.5 3.5 2M15 10h3M15 13h3"/>'),
 house:G('<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>'),
 work:G('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5h6v2M3 12h18"/>'),
 tax:G('<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4M9 14l6-3"/>'),
 bank:G('<path d="M3 9l9-5 9 5M5 9v9M9.5 9v9M14.5 9v9M19 9v9M3 20h18"/>'),
 shield:G('<path d="M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>'),
 umbrella:G('<path d="M3 12a9 9 0 0118 0z"/><path d="M12 12v6a2 2 0 004 0"/>'),
 car:G('<path d="M4 16v-4l2-5h12l2 5v4z"/><circle cx="8" cy="16" r="2"/><circle cx="16" cy="16" r="2"/>'),
 kids:G('<circle cx="8" cy="7" r="3"/><circle cx="17" cy="9" r="2"/><path d="M3 20c0-4 2-7 5-7s5 3 5 7M14 20c0-3 1-5 3-5s3 2 3 5"/>'),
 building:G('<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1"/>'),
 name:G('<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4M9 13h6M9 17h4"/>'),
 cap:G('<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>'),
 scale:G('<path d="M12 3v18M5 7h14M5 7l-3 6a3 3 0 006 0zM19 7l-3 6a3 3 0 006 0zM8 21h8"/>'),
 spark:G('<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>'),
 star:G('<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>'),
 globe:G('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>'),
 check:G('<path d="M5 12l5 5 9-10"/>'),
 lock:G('<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/>'),
 cloud:G('<path d="M7 18a4 4 0 010-8 6 6 0 0111.5 1.5A3.5 3.5 0 0118 18z"/>'),
 up:G('<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"/>'),
 mail:G('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>'),
 gear:G('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>'),
 clock:G('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
 send:G('<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>'),
 search:G('<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>'),
 alert:G('<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>'),
 van:G('<path d="M2 16V7h13l5 5v4z"/><path d="M15 7v5h5"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/>'),
 paw:G('<circle cx="6" cy="10" r="2"/><circle cx="10" cy="6" r="2"/><circle cx="14" cy="6" r="2"/><circle cx="18" cy="10" r="2"/><path d="M12 12c-3 0-6 4-6 6.5 0 1.5 1.5 2 3 1.5 1-.3 2-.8 3-.8s2 .5 3 .8c1.5.5 3 0 3-1.5 0-2.5-3-6.5-6-6.5z"/>'),
 key:G('<circle cx="8" cy="14" r="4"/><path d="M11 11l8-8M16 6l2 2"/>'),
 tag:G('<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>'),
 plus:G('<path d="M12 5v14M5 12h14"/>'),
 archive:G('<rect x="3" y="4" width="18" height="5" rx="1"/><path d="M5 9v11h14V9M10 13h4"/>'),
 drive:G('<rect x="3" y="13" width="18" height="6" rx="2"/><path d="M5 13l2-8h10l2 8"/>'),
 heart:G('<path d="M12 20s-7-4.5-9-9a4.5 4.5 0 018-4 4.5 4.5 0 018 4c-2 4.5-7 9-7 9z"/>'),
 sparkles:G('<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>')
};
IC.user = G('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/>');
IC.eye = G('<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>');
IC.sync = G('<path d="M20 11a8 8 0 00-14.5-4.5L3 9M4 13a8 8 0 0014.5 4.5L21 15"/><path d="M3 4v5h5M21 20v-5h-5"/>');
IC.bug = G('<rect x="7" y="8" width="10" height="12" rx="5"/><path d="M12 8V5M9 5l1 2M15 5l-1 2M3 13h4M17 13h4M4 19l3-2M20 19l-3-2M4 7l3 2M20 7l-3 2"/>');
IC.history = G('<path d="M3 12a9 9 0 109-9 9 9 0 00-7 3.4L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>');
IC.chip = G('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>');
IC.book = G('<path d="M4 4h6a2 2 0 012 2v14a2 2 0 00-2-2H4zM20 4h-6a2 2 0 00-2 2v14a2 2 0 012-2h6z"/>');
IC.palette = G('<path d="M12 3a9 9 0 100 18c1 0 1.5-.8 1.5-1.5 0-1-.8-1.4-.8-2.3 0-1 .8-1.7 1.8-1.7H17a4 4 0 004-4c0-4.7-4-8.5-9-8.5z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>');
IC.calendar = G('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>');
IC.trash = G('<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>');
