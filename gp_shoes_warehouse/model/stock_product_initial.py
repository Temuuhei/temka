# -*- coding: utf-8 -*-
##############################################################################
#
#    Asterisk Technologies LLC, Enterprise Management Solution    
#    Copyright (C) 2007-2013 Game of Code LLC Co.,ltd (<http://www.erp.mn>). All Rights Reserved
#
#    Email : temuujintsogt@gmail.com
#    Phone : 976 + 99741074,976 + 91586182
#
##############################################################################

from odoo import osv, fields, models
from datetime import date
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.netsvc, decimal, base64, os, time, xlrd
from tempfile import NamedTemporaryFile
from datetime import datetime
import logging
from operator import itemgetter



class StockProductInitial(models.TransientModel):
    _name = 'stock.product.initial'
    _description = 'Stock Product Initial'
    
    date =  fields.Datetime('Date Of Inventory', required=True, default = date.today().strftime('%Y-%m-%d'))
    location_id = fields.Many2one('stock.location', 'Warehouse', required=True)
    data = fields.Binary('Excel File', required=True)
    type = fields.Selection([('default_code','Default code'),('name','Name')], 'Import type', required=True, default = 'default_code')
    categ_id = fields.Many2one('product.category', u'Барааны ангилал', required=True)
    # _defaults = {
    #     'type':'default_code',
    # }

    def import_data(self, wiz):
        print'\n\n\n Input complete'
        wiz = self
        context = self._context or {}
        product_obj = self.env['product.product']
        product_tmpl_obj = self.env['product.template']
        product_category_obj = self.env['product.category']
        product_uom_obj = self.env['product.uom']
        inventory_obj = self.env['stock.inventory']
        inventory_line_obj = self.env['stock.inventory.line']
        Inventory = self.env['stock.inventory']
        product_att = self.env['product.attribute.value']
        product_uoms = {u'ш': 'Unit(s)'}



        fileobj = NamedTemporaryFile('w+')
        fileobj.write(base64.decodestring(wiz.data))
        fileobj.seek(0)

        if not os.path.isfile(fileobj.name):
            raise osv.except_osv(u'Алдаа',
                                 u'Мэдээллийн файлыг уншихад алдаа гарлаа.\nЗөв файл эсэхийг шалгаад дахин оролдоно уу!')
        book = xlrd.open_workbook(fileobj.name)
        sheet = book.sheet_by_index(0)
        nrows = sheet.nrows
        print '\n\n\n\n ROWS', nrows

        rowi = 1

        while rowi < nrows:
            try:
                row = sheet.row(rowi)
                code = row[0].value
                # print'Internal Code \n\n\n',code
                product_type = 'product'
                product_supply_method = 'buy'
                product_procure_method = 'make_to_stock'
                product_sale_ok = True
                product_purchase_ok = True
                product_cost_method = 'average'
                product_valuation = 'real_time'

                have_prod = product_obj.search([('default_code', '=', row[0].value)])
                if not have_prod:
                    print 'Барааны код олдоогүй ба шууд үүсгэх ------------------>', have_prod
                    values_pro_tmp = {
                        'name': sheet.name,
                        'categ_id': self.categ_id.id,
                        'standard_price':row[5].value or 9999,
                        'list_price':row[1].value or 9999,
                        'uom_id': 1,
                        'type': product_type,
                        'purchase_line_warn': 'no-message',
                        'sale_line_warn': 'no-message',
                        'tracking': 'none',
                        'purchase_ok': True,
                        'sale_ok': True,
                        'company_id': 1,
                    }
                    # print'\n\n\n\n Values',values_pro_tmp
                    product_tmpl_id = product_tmpl_obj.create(values_pro_tmp)
                    # print 'Барааны код олдоогүй ба шууд үүсгэсэн Produc Template ------------------>',product_tmpl_id,row[0].value
                    att_ids = []
                    if row[2].value is not None:
                        product_attribute_value_size = self.env['product.attribute.value'].search(
                            [('name', '=', str(row[2].value)[:2])])
                        # print'Дараах утгатай %s %s-н id-тай барааны шинж байгаа эсэхийг шалгаж эхэлж байна' %(str(row[2].value)[:2],product_attribute_value_size)
                        if product_attribute_value_size:
                            att_ids.append(product_attribute_value_size[0].id)
                        product_att_line = self.env['product.attribute.line'].search(
                            [('product_tmpl_id', '=', product_tmpl_id.id),
                             ('attribute_id', '=', product_attribute_value_size[0].attribute_id.id)])
                        # print'Барааны хувилбар буюу Product Template-д шинжийг нэмж эхэлж байа ====================='
                        if not product_att_line:
                            product_att_line = self.env['product.attribute.line'].create(
                                {'product_tmpl_id': product_tmpl_id.id,
                                 'attribute_id':
                                     product_attribute_value_size[0].attribute_id.id})
                            # print'Нэмэгдсэн Product Attribute Line ------------------->',product_att_line
                        # print'Барааны хувилбар баганад үүсгэж эхэлж байна ==========================='
                        product_att_line.value_ids = [(6, 0, product_attribute_value_size.ids)]
                        # print'\n Үүссэн бичиглэлүүд Хувилбар баганад \n', product_att_line.value_ids
                        # print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------'
                        if row[4].value:
                            # print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------', str(row[4].value)
                            product_attribute_value_season = self.env['product.attribute.value'].search(
                                [('name', '=', str(row[4].value))])
                            if product_attribute_value_season:
                                att_ids.append(product_attribute_value_season.id)
                            product_att_line = self.env['product.attribute.line'].search(
                                [('product_tmpl_id', '=', product_tmpl_id.id),
                                 ('attribute_id', '=', product_attribute_value_season.attribute_id.id)])
                            if not product_att_line:
                                product_att_line = self.env['product.attribute.line'].create(
                                    {'product_tmpl_id': product_tmpl_id.id,
                                     'attribute_id':
                                         product_attribute_value_season.attribute_id.id})
                                # print'Нэмэгдсэн Product Attribute Line Улирал ------------------->', product_att_line
                            product_att_line.value_ids = [(6, 0, product_attribute_value_season.ids)]


                        product_id = product_obj.create({
                            'product_tmpl_id': product_tmpl_id.id,
                            'active': True,
                            'valuation': product_valuation,
                            'default_code': code,
                            'standart_price': row[5].value or 9999,
                            'attribute_value_ids': [(6, 0, att_ids)],
                        })
                    if row[3].value is not None:
                        # print'Агуулахын код'
                        line_data = {
                            'product_qty': row[3].value,
                            'location_id': wiz.location_id.id,
                            'product_id': product_id.id,
                            'product_uom_id': product_id.uom_id.id,
                            'theoretical_qty': 0,
                            'prod_lot_id': None,
                        }
                        # print'\n\n %s \n\n' % line_data
                        inventory_filter = 'product'
                        inventory = Inventory.create({
                            'name': _('INV- %s: %s -%s') %(wiz.location_id,product_id.name,product_id.default_code),
                            'filter': inventory_filter,
                            'product_id': product_id.id,
                            'location_id': wiz.location_id.id,
                            'lot_id': None,
                            'line_ids': [(0, 0, line_data)],
                        })
                        inventory.action_done()
                        # print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ Шинээр бараа үүсгэж тоолсон :)))*****'
                else:
                    # print'RIGHT Congratz'
                    att_ids = []
                    check = True
                    product_attribute_value_size = self.env['product.attribute.value'].search(
                        [('name', '=', str(row[2].value)[:2])])
                    product_attribute_value_season = self.env['product.attribute.value'].search(
                        [('name', '=', str(row[4].value))])
                    if product_attribute_value_size:
                        att_ids.append(product_attribute_value_size.id)
                        if product_attribute_value_season:
                            att_ids.append(product_attribute_value_season.id)
                    for have in have_prod:
                        if len(have.attribute_value_ids) == len(att_ids):
                            a = set(have.attribute_value_ids)
                            b = set(att_ids)
                            diff = a.difference(b)
                            if diff is False:
                                # print'-------------------- Энэ бараа байсан ба шууд Барааны тоо хэмжээг л өөрчилсөн',have_prod
                                if row[3].value is not None:
                                    # print'Агуулахын код'
                                    line_data = {
                                        'product_qty': row[3].value,
                                        'location_id': wiz.location_id.id,
                                        'product_id': have.id,
                                        'product_uom_id': have.uom_id.id,
                                        'theoretical_qty': 0,
                                        'prod_lot_id': None,
                                    }
                                    # print'\n\n %s \n\n' % line_data
                                    inventory_filter = 'product'
                                    inventory = Inventory.create({
                                        'name': _('INV- %s: %s -%s') % (
                                        wiz.location_id, have.name, have.default_code),
                                        'filter': inventory_filter,
                                        'product_id': have.id,
                                        'location_id': wiz.location_id.id,
                                        'lot_id': None,
                                        'line_ids': [(0, 0, line_data)],
                                    })
                                    inventory.action_done()
                                    # print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ Шинээр бараа үүсгэж тоолсон :)))*****'
                                    check = False
                                    break
                    if check == True:
                        new_att_ids =[]
                        product_att_line = self.env['product.attribute.line'].search(
                            [('product_tmpl_id', '=', have_prod[0].product_tmpl_id.id),
                             ('attribute_id', '=', product_attribute_value_size[0].attribute_id.id)])
                        # print'Барааны хувилбар буюу Product Template-д шинжийг нэмж эхэлж байа ====================='
                        if not product_att_line:
                            product_att_line = self.env['product.attribute.line'].create(
                                {'product_tmpl_id': have_prod[0].product_tmpl_id.id,
                                 'attribute_id':
                                     product_attribute_value_size[0].attribute_id.id})
                        new_att_ids.append(product_attribute_value_size[0].id)
                        # print'GOYYYYYYYYYYYYYYYYYYYYYYYYYYYy',product_att_line.value_ids
                        if product_attribute_value_size not in product_att_line.value_ids:
                            # print'Нэмэгдсэн Product Attribute Line ------------------->', product_att_line
                            # print'Барааны хувилбар баганад үүсгэж эхэлж байна ==========================='
                            product_att_line.value_ids = [(6, 0, product_attribute_value_size.ids)]
                        if row[4].value:
                            # print'Улирлын утга байгаа эсэхийг шалгаж байна ----------------------', str(row[4].value)
                            product_attribute_value_season = self.env['product.attribute.value'].search(
                                [('name', '=', str(row[4].value))])
                            product_att_line = self.env['product.attribute.line'].search(
                                [('product_tmpl_id', '=', have_prod[0].product_tmpl_id.id),
                                 ('attribute_id', '=', product_attribute_value_season.attribute_id.id)])
                            if not product_att_line:
                                product_att_line = self.env['product.attribute.line'].create(
                                    {'product_tmpl_id': have_prod[0].product_tmpl_id.id,
                                     'attribute_id':
                                         product_attribute_value_season.attribute_id.id})

                                # print'Нэмэгдсэн Product Attribute Line Улирал ------------------->', product_att_line
                            new_att_ids.append(product_attribute_value_season[0].attribute_id.id)
                            product_att_line.value_ids = [(6, 0, product_attribute_value_season[0].ids)]

                            # print'\n\nTemka', have
                        product_id = product_obj.create({
                            'product_tmpl_id': have_prod[0].product_tmpl_id.id,
                            'active': True,
                            'valuation': product_valuation,
                            'default_code': code,
                            'standart_price': row[1].value or 9999,
                            'attribute_value_ids': [(6, 0, new_att_ids)],
                        })
                        if row[3].value is not None:
                            # print'Агуулахын код'
                            line_data = {
                            'product_qty': row[3].value,
                                'location_id': wiz.location_id.id,
                                'product_id': product_id.id,
                                'product_uom_id': product_id.uom_id.id,
                                'theoretical_qty': 0,
                                'prod_lot_id': None,
                            }
                            # print'\n\n %s \n\n' % line_data
                            inventory_filter = 'product'
                            inventory = Inventory.create({
                                'name': _('INV-%s: %s - %s') % (
                                wiz.location_id, product_id.name, product_id.default_code),
                                'filter': inventory_filter,
                                'product_id': product_id.id,
                                'location_id': wiz.location_id.id,
                                'lot_id': None,
                                'line_ids': [(0, 0, line_data)],
                            })
                            inventory.action_done()
                            # print'***** Амжилттай тооллого хийж барааны гарт байгаа хэмжээг нэмлээ $$$$$$$$$$$$'
                rowi += 1
            except IndexError:
                raise UserError(_('Excel sheet must be 6 columned : Code, Price,Size,Qty,Season,Cost: error on row %s ' % rowi))
        return True
