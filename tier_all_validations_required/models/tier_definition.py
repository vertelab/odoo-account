# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class TierDefinition(models.Model):
    _inherit = "tier.definition"

    reviewers_validations_required = fields.Boolean(default=False, String="All reviewers validations required") ### attesterare

    
# ~ class AccountMove(models.Model):
    # ~ _inherit = "res.users"
    # ~ validation_needed_invoice_id = fields.Many2one('account.move',string='Move Validator') ### attesterare
    

class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"
    
    def _get_sequences_to_approve(self, user):
        ###########Changes
        _logger.warning("_get_sequences_to_approve")
        _logger.warning("_get_sequences_to_approve")
        _logger.warning("_get_sequences_to_approve")
        _logger.warning("_get_sequences_to_approve")
        _logger.warning("_get_sequences_to_approve")
        _logger.warning("_get_sequences_to_approve")
        _logger.warning("_get_sequences_to_approve")
        all_reviews = self.review_ids.filtered(lambda r: r.status == "pending" or  r.status == "partial_approved")
        my_reviews = all_reviews.filtered(lambda r: user in r.reviewer_ids)
        _logger.warning(f"{my_reviews=}")
        
        #my_reviews = my_reviews.filtered(lambda r: user not in r.reviewer_ids.done_by_all)
        
        my_reviews2 = []
        _logger.warning(f"{my_reviews=}")
        for review in my_reviews:
            if user not in review.done_by_all:
                my_reviews2.append(review)
        _logger.warning(f"{my_reviews2=}")
        my_reviews = my_reviews2
            
        ###########Changes

        
        
        # Include all my_reviews with approve_sequence = False
        sequences = my_reviews.filtered(lambda r: not r.approve_sequence).mapped(
            "sequence"
        )
        # Include only my_reviews with approve_sequence = True
        approve_sequences = my_reviews.filtered("approve_sequence").mapped("sequence")
        if approve_sequences:
            my_sequence = min(approve_sequences)
            min_sequence = min(all_reviews.mapped("sequence"))
            if my_sequence <= min_sequence:
                sequences.append(my_sequence)
        return sequences


    

    
    def _validate_tier(self, tiers=False):
        self.ensure_one()
        tier_reviews = tiers or self.review_ids
        user_reviews = tier_reviews.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
            
        for tier in user_reviews:
            _logger.warning(f"{tier.definition_id}")
            _logger.warning(f"{tier.definition_id.reviewers_validations_required}")
            
        multi_reviews = user_reviews.filtered(lambda t: t.reviewers_validations_required == True)
        _logger.warning(f"{multi_reviews=}")
        
        regular_reviews = user_reviews.filtered(lambda t: t.reviewers_validations_required == False)
        _logger.warning(f"{regular_reviews=}")
        
        
        
        multi_reviews.write(
            {
                "done_by_all": [(4,self.env.user.id,0)],
            }
        )
        
        for review in multi_reviews:
            if review.done_by_all == review.todo_by:
                review.status = "approved"
                review.reviewed_date = fields.Datetime.now()
            else:
                review.status = "partial_approved"

        return super(TierValidation, self)._validate_tier(regular_reviews)

class TierReview(models.Model):
    _inherit = "tier.review"
    status = fields.Selection(selection_add=[("partial_approved", "Partially approved")], ondelete={'partial_approved': 'set default'})
    
    done_by_all = fields.Many2many(comodel_name="res.users",relation="done_validations" )
    reviewers_validations_required = fields.Boolean(related='definition_id.reviewers_validations_required', readonly=True)
    
    def _can_review_value(self):
        _logger.warning(f"{self}")
        if self.status != "pending" and self.status != "partial_approved" :
            _logger.warning(f"status 1{self.status}")
            return False
        if not self.approve_sequence:
            _logger.warning(f"approve_sequence 2{self.approve_sequence}")
            return True
        resource = self.env[self.model].browse(self.res_id)
        reviews = resource.review_ids.filtered(lambda r: r.status == "pending")
        partial_reviews = resource.review_ids.filtered(lambda r: r.status == "partial_approved")
        if not reviews and not partial_reviews:
            return True
        sequence = min(reviews.mapped("sequence"))
        return self.sequence == sequence
    
    
    
    

