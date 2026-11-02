/**
 * FOSS4G NA 2026 · 1-month trial sign-up — instant welcome email.
 *
 * Install (from the Lutra Google account, once):
 *   1. Go to script.google.com → "New project" (a standalone project, NOT from the form's menu).
 *   2. Replace the editor contents with this file and save.
 *   3. Pick "setup" in the function menu and press Run. Approve the permissions.
 * After that, every new response gets the email below, sent from the account
 * that ran setup (your Lutra Gmail). Gmail's daily sending limit applies
 * (about 1,500 a day on Google Workspace), far more than a talk needs.
 * Your Lutra account needs edit access to the form (already shared).
 */

const FORM_ID = '1bDZbSv9fL9CUuJ4XEcnATAlSPdMw9bMwRPUF3u6CQi8';
const REGISTER_URL = 'https://app.merginmaps.com/register';
const SENDER_NAME = 'Vitor Vieira · Mergin Maps';
const SUBJECT = 'Your free month of Mergin Maps: one step left';

function sendWelcome(e) {
  const answers = {};
  e.response.getItemResponses().forEach(r => {
    answers[r.getItem().getTitle().trim()] = String(r.getResponse() || '').trim();
  });
  const email = answers['Email'];
  if (!email) return;

  const text =
    'Hi,\n\n' +
    'Thanks for coming to my talk at FOSS4G NA 2026!\n\n' +
    'To get your free month of Mergin Maps, create your account here:\n' +
    REGISTER_URL + '\n\n' +
    'Sign up with this same email address (' + email + ') so we can match it and extend your trial.\n\n' +
    'Any questions, just reply to this email.\n\n' +
    'Vitor Vieira\nLutra Consulting · merginmaps.com';

  const html =
    '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#1d2b27;max-width:520px">' +
    '<p>Hi,</p>' +
    '<p>Thanks for coming to my talk at FOSS4G NA 2026!</p>' +
    '<p>To get your <b>free month of Mergin Maps</b>, create your account here:</p>' +
    '<p><a href="' + REGISTER_URL + '" style="display:inline-block;background:#66c68f;color:#00423c;' +
    'font-weight:bold;text-decoration:none;padding:12px 22px;border-radius:24px">Complete your registration</a></p>' +
    '<p>Sign up with this same email address (<b>' + email + '</b>) so we can match it and extend your trial.</p>' +
    '<p>Any questions, just reply to this email.</p>' +
    '<p>Vitor Vieira<br><span style="color:#6b7a74">Lutra Consulting · merginmaps.com</span></p>' +
    '</div>';

  GmailApp.sendEmail(email, SUBJECT, text, { htmlBody: html, name: SENDER_NAME });
}

/** Run once: makes sendWelcome fire on every new form response. */
function setup() {
  const form = FormApp.openById(FORM_ID);
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'sendWelcome')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('sendWelcome').forForm(form).onFormSubmit().create();
  Logger.log('Auto-email is on for: ' + form.getTitle());
}
