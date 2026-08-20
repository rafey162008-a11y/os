"""Customer support routes: tickets, help center, live chat UI."""
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import current_user

from app.extensions import db
from app.models.commerce import SupportTicket, SupportReply, Notification
from app.forms.customer_forms import SupportTicketForm, TicketReplyForm
from app.utils.decorators import customer_required
from app.utils.activity import log_action

support_bp = Blueprint('support', __name__)


@support_bp.route('/help')
def help_center():
    return render_template('customer/help_center.html')


@support_bp.route('/tickets')
@customer_required
def my_tickets():
    tickets = SupportTicket.query.filter_by(customer_id=current_user.id) \
        .order_by(SupportTicket.created_at.desc()).all()
    return render_template('customer/my_tickets.html', tickets=tickets)


@support_bp.route('/tickets/new', methods=['GET', 'POST'])
@customer_required
def new_ticket():
    form = SupportTicketForm()
    if form.validate_on_submit():
        ticket = SupportTicket(
            customer_id=current_user.id,
            subject=form.subject.data,
            category=form.category.data,
            priority=form.priority.data,
            message=form.message.data,
            status='open',
        )
        db.session.add(ticket)
        db.session.commit()
        log_action('create', 'support_ticket', ticket.id,
                   f'{current_user.full_name} created support ticket {ticket.ticket_number}')
        flash(f'Your support ticket {ticket.ticket_number} has been created.', 'success')
        return redirect(url_for('support.ticket_detail', ticket_id=ticket.id))
    return render_template('customer/ticket_form.html', form=form)


@support_bp.route('/tickets/<int:ticket_id>', methods=['GET', 'POST'])
@customer_required
def ticket_detail(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id)
    if not ticket or ticket.customer_id != current_user.id:
        abort(404)
    form = TicketReplyForm()
    if form.validate_on_submit():
        reply = SupportReply(
            ticket_id=ticket.id,
            user_id=current_user.id,
            message=form.message.data,
            is_staff=False,
        )
        db.session.add(reply)
        if ticket.status == 'closed':
            ticket.status = 'open'
        db.session.commit()
        flash('Your reply has been sent.', 'success')
        return redirect(url_for('support.ticket_detail', ticket_id=ticket.id))
    return render_template('customer/ticket_detail.html', ticket=ticket, form=form)


@support_bp.route('/tickets/<int:ticket_id>/close', methods=['POST'])
@customer_required
def close_ticket(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id)
    if not ticket or ticket.customer_id != current_user.id:
        abort(404)
    ticket.status = 'closed'
    db.session.commit()
    flash('Ticket closed.', 'info')
    return redirect(url_for('support.ticket_detail', ticket_id=ticket.id))
