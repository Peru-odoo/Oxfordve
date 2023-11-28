# -*- coding: utf-8 -*-

from odoo import _, api, exceptions, fields, models


class CommissionCommission(models.AbstractModel):
    _name = 'commission.commission'
    _description = 'Commissions'

    name = fields.Char(string="Nombre", required=True)
    commission_type = fields.Selection(
        [('fija', 'Fija'), ('basada_en_otra_comision', 'Basada en otra Comisión')],
        string='Tipo de comisión',
        required=True,
        default='fija'
    )

    cant_minima_base = fields.Float(string='Can. Mín. Base', required=True)
    bono_base = fields.Float(string='Bono Base', required=True)

    basado_en = fields.Many2one(
        comodel_name='commission.commission',
        string="Basado en",
        domain="[('id', '!=', id)]"
    )
    cant_min_base_factor_divisor = fields.Float(
        string='Factor divisor Cant. Mín.',
        default=1.0
    )
    cant_min_base_factor_multiplicador = fields.Float(
        string='Factor multiplicador Cant. Mín.',
        default=1.0
    )
    cant_min_base_factor_extra = fields.Float(string='Factor extra Cant. Mín.')
    bono_base_factor_divisor = fields.Float(string='Factor divisor Bono B.', default=1.0)
    bono_base_factor_multiplicador = fields.Float(
        string='Factor multiplicador Bono B.',
        default=1.0
    )
    bono_base_factor_extra = fields.Float(string='Factor extra Bono B.')

    forma_de_calculo = fields.Selection(
        [('fijo', 'Fijo'), ('regla_de_tres', 'Regla de tres')],
        string='Forma de cálculo',
        default='fijo'
    )

    base_min_qty = fields.Float(
        string='Cantidad mínima base',
        compute="_compute_base_min_qty",
        recursive=True,
        store=True,
    )
    basic_bonus = fields.Float(
        string='Bono básico',
        compute="_compute_basic_bonus",
        recursive=True,
        store=True,
    )

    _sql_constraints = [
        (
            'cant_min_fd_not_zero',
            'CHECK(cant_min_base_factor_divisor != 0)',
            'El factor divisor no puede ser cero. Por favor, verifique'
        ),
        (
            'bono_fd_not_zero',
            'CHECK(bono_base_factor_divisor != 0)',
            'El factor divisor no puede ser cero. Por favor, verifique'
        ),
    ]

    @api.depends(
        "commission_type",
        "cant_minima_base",
        "cant_min_base_factor_divisor",
        "cant_min_base_factor_multiplicador",
        "cant_min_base_factor_extra",
        "basado_en",
        "basado_en.base_min_qty",
    )
    def _compute_base_min_qty(self):
        for commission in self:
            if commission.commission_type == 'basada_en_otra_comision':
                if commission.cant_min_base_factor_divisor > 0:
                    commission.base_min_qty = (
                        (commission.basado_en.base_min_qty / commission.cant_min_base_factor_divisor) *
                        commission.cant_min_base_factor_multiplicador
                    ) + commission.cant_min_base_factor_extra
            elif commission.commission_type == 'fija':
                commission.base_min_qty = commission.cant_minima_base

    @api.depends(
        "commission_type",
        "bono_base",
        "bono_base_factor_divisor",
        "bono_base_factor_multiplicador",
        "bono_base_factor_extra",
        "basado_en",
        "basado_en.basic_bonus",
    )
    def _compute_basic_bonus(self):
        for commission in self:
            if commission.commission_type == 'basada_en_otra_comision':
                if commission.bono_base_factor_divisor > 0:
                    commission.basic_bonus = (
                        (commission.basado_en.basic_bonus / commission.bono_base_factor_divisor) *
                        commission.bono_base_factor_multiplicador
                    ) + commission.bono_base_factor_extra
            elif commission.commission_type == 'fija':
                commission.basic_bonus = commission.bono_base

    def compute_commission(self, total_sales_amount=0.0):
        self.ensure_one()
        amount = 0.0

        if self.forma_de_calculo == 'fijo':
            amount = self.basic_bonus
        elif self.forma_de_calculo == 'regla_de_tres' and self.base_min_qty > 0:
            amount = total_sales_amount * self.basic_bonus / self.base_min_qty

        return amount


class ConfigurationCollection(models.Model):
    _name = "configuration.collection"
    _description = "Configuración del porcentaje a pagar por las cobranzas realizadas"

    name = fields.Char(string="Nombre", default=" ")
    percentage = fields.Float(string="Porcentaje (%) de comisión", required=True)

    @api.model
    def _account_ids_domain(self):
        return [('user_type_id', '=', self.env.ref('account.data_account_type_liquidity').id)]

    account_ids = fields.Many2many(
        'account.account',
        'collection_id',
        string="Cuentas contables a considerar",
        required=True,
        domain=_account_ids_domain,
    )

    _sql_constraints = [
        (
            'percentage_not_zero',
            'CHECK(percentage >= 0)',
            'El porcentaje no puede ser un número negativo. Por favor, verifique'
        ),
    ]

    @api.model
    def create(self, vals):
        res = super(ConfigurationCollection, self).create(vals)

        if res.id:
            configs = self.search(["id", "!=", res.id])
            account_ids = configs.account_ids
            configs.unlink()
            account_ids.collection_id = res.id

        return res

    def write(self, values):
        res = super(ConfigurationCollection, self).write(values)

        if res and self.id:
            self.env['account.account'].search([
                ('user_type_id', '=', self.env.ref("account.data_account_type_liquidity").id),
                ('collection_id', '=', self.id)
            ]).collection_id = False

            self.account_ids.collection_id = self.id

        return res
