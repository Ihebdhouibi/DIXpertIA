import auth from './messages/auth';
import common from './messages/common';
import dashboard from './messages/dashboard';
import home from './messages/home';
import invoices from './messages/invoices';
import people from './messages/people';

/** Every message, both languages (#135). One file per area, see ./define.ts. */
export const catalog = {
  ...common,
  ...auth,
  ...dashboard,
  ...invoices,
  ...people,
  ...home,
};

export type MessageKey = keyof typeof catalog;
