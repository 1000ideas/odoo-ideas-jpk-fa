# -*- coding: utf-8 -*-

import base64
import datetime
import pytz
import re
import sys
import xml.dom.minidom
from odoo import models, fields, api
from dateutil.relativedelta import *

class ideas_jpk_fa(models.TransientModel):
    _name = 'ideas_jpk_fa.generator'

    dateStart = fields.Date(default=lambda *a: (datetime.datetime.now()+relativedelta(months=-1)).strftime('%Y-%m-%d'), required=True)
    dateEnd = fields.Date(default=lambda *a: datetime.datetime.now().strftime('%Y-%m-%d'), required=True)
    company = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, required=True)
    currency = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, domain="[('active', '=', 'TRUE')]", required=True)
    purpose = fields.Selection([
            ('1', 'złożenie'),
            ('2', 'korekta'),
    ], default="1", required=True)
    regon = fields.Char(required=False)
    uscode = fields.Char(required=True)
    county = fields.Char(required=True)
    municipality = fields.Char(required=True)
    post = fields.Char(required=True)
    street = fields.Char(required=False)
    buildingNumber = fields.Char(required=True)
    flatNumber = fields.Char(required=False)

    @api.multi
    def generate_file(self):
        local_tz = pytz.timezone(self.env.user.tz or 'UTC')

        invoices = self.env['account.invoice'].search([
                        ('date_invoice', '>=', self.dateStart),
                        ('date_invoice', '<=', self.dateEnd),
                        ('company_id', '=', self.company.id),
                        ('currency_id', '=', self.currency.id),
                        ('type', 'in', ('out_invoice', 'out_refund',)),
                        ('state', 'in', ('paid', 'open',))
        ])

        print(len(invoices))

        doc = xml.dom.minidom.Document()
        # JPK - root element
        jpk = doc.createElementNS('http://jpk.mf.gov.pl/wzor/2016/03/09/03095/', 'JPK')
        jpk.setAttribute("xmlns", "http://jpk.mf.gov.pl/wzor/2016/03/09/03095/")
        jpk.setAttribute("xmlns:etd", "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2016/01/25/eD/DefinicjeTypy/")

        # Naglowek
        naglowek = doc.createElement('Naglowek')

        kodFormularza = doc.createElement('KodFormularza')
        kodFormularza.setAttribute("kodSystemowy", "JPK_FA (1)")
        kodFormularza.setAttribute("wersjaSchemy", "1-0")
        kodFormularza.appendChild(doc.createTextNode("JPK_FA"))
        naglowek.appendChild(kodFormularza)
        naglowek.appendChild(self.create_element(doc, 'WariantFormularza', '1'))
        naglowek.appendChild(self.create_element(doc, 'CelZlozenia', self.purpose))
        local_date = datetime.datetime.now().astimezone(local_tz).strftime('%Y-%m-%dT%H:%M:%S')
        naglowek.appendChild(self.create_element(doc, 'DataWytworzeniaJPK', local_date))
        naglowek.appendChild(self.create_element(doc, 'DataOd', self.dateStart))
        naglowek.appendChild(self.create_element(doc, 'DataDo', self.dateEnd))
        naglowek.appendChild(self.create_element(doc, 'DomyslnyKodWaluty', self.currency.name))
        naglowek.appendChild(self.create_element(doc, 'KodUrzedu', self.uscode))

        jpk.appendChild(naglowek)

        # Podmiot1
        podmiot1 = doc.createElement('Podmiot1')

        identyfikatorPodmiotu = doc.createElement('IdentyfikatorPodmiotu')
        sVat = re.split('(\d+)',str(self.company.partner_id.vat).strip())
        if sVat:
            if len(sVat) > 1:
                identyfikatorPodmiotu.appendChild(self.create_element(doc, 'etd:NIP', sVat[1]))
            else:
                identyfikatorPodmiotu.appendChild(self.create_element(doc, 'etd:NIP', self.company.partner_id.vat))

        identyfikatorPodmiotu.appendChild(self.create_element(doc, 'etd:PelnaNazwa', self.company.partner_id.name))
        if self.regon:
            identyfikatorPodmiotu.appendChild(self.create_element(doc, 'etd:REGON', self.regon))
        podmiot1.appendChild(identyfikatorPodmiotu)
        adresPodmiotu = doc.createElement('AdresPodmiotu')
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:KodKraju', self.company.partner_id.country_id.code))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:Wojewodztwo', self.company.partner_id.state_id.name))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:Powiat', self.county))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:Gmina', self.municipality))
        if self.street:
            adresPodmiotu.appendChild(self.create_element(doc, 'etd:Ulica', self.street))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:NrDomu', self.buildingNumber))
        if self.flatNumber:
            adresPodmiotu.appendChild(self.create_element(doc, 'etd:NrLokalu', self.flatNumber))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:Miejscowosc', self.company.partner_id.city))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:KodPocztowy', self.company.partner_id.zip))
        adresPodmiotu.appendChild(self.create_element(doc, 'etd:Poczta', self.post))

        podmiot1.appendChild(adresPodmiotu)

        jpk.appendChild(podmiot1)

        # Faktura - collection
        invoicesTotalValue = 0
        for i in invoices:
            v23_val = 0
            v23_tax = 0
            v8_val = 0
            v8_tax = 0
            v5_val = 0
            v5_tax = 0
            v0_val = 0
            vz_val = 0
            vunknown_val = 0
            vunknown_tax = 0

            invoicesTotalValue += i.amount_total
            faktura = doc.createElement('Faktura')
            faktura.setAttribute("typ", "G")
            faktura.appendChild(self.create_element(doc, 'P_1', i.date))
            faktura.appendChild(self.create_element(doc, 'P_2A', i.number))
            faktura.appendChild(self.create_element(doc, 'P_3A', i.partner_id.name))
            faktura.appendChild(self.create_element(doc, 'P_3B', ( str(i.partner_id.city) + ' ' + str(i.partner_id.zip)) + ', ' + str(i.partner_id.street) ))
            faktura.appendChild(self.create_element(doc, 'P_3C', self.company.partner_id.name))
            faktura.appendChild(self.create_element(doc, 'P_3D', str(self.company.partner_id.city) + ' ' + str(self.company.partner_id.zip) + ', ' + str(self.company.partner_id.street) ))

            sVat = re.split('(\d+)',str(self.company.partner_id.vat).strip())
            if sVat:
                if len(sVat) > 1:
                    if sVat[0]:
                        faktura.appendChild(self.create_element(doc, 'P_4A', sVat[0]))
                    faktura.appendChild(self.create_element(doc, 'P_4B', sVat[1]))
                else:
                    faktura.appendChild(self.create_element(doc, 'P_4B', self.company.partner_id.vat))

            bVat = re.split('(\d+)',str(i.partner_id.vat).strip())
            if bVat:
                if len(bVat) > 1:
                    if bVat[0]:
                        faktura.appendChild(self.create_element(doc, 'P_5A', bVat[0]))
                    faktura.appendChild(self.create_element(doc, 'P_5B', bVat[1]))
                else:
                    faktura.appendChild(self.create_element(doc, 'P_5B', i.partner_id.vat))

            faktura.appendChild(self.create_element(doc, 'P_6', i.date_invoice))
            for t in i.tax_line_ids:
                if t.tax_id.description == 'V23' or t.tax_id.description == 'V22':
                    v23_val += round(t.base, 2)
                    v23_tax += round(t.amount, 2)
                elif t.tax_id.description == 'V8' or t.tax_id.description == 'V7':
                    v8_val += round(t.base, 2)
                    v8_tax += round(t.amount, 2)
                elif t.tax_id.description == 'V5':
                    v5_val += round(t.base, 2)
                    v5_tax += round(t.amount, 2)
                elif t.tax_id.description == 'V0':
                    v0_val += round(t.base, 2)
                elif t.tax_id.description == 'VZW' or t.tax_id.description == 'NP':
                    vz_val += round(t.base, 2)
                else:
                    vunknown_val += round(t.base, 2)
                    vunknown_tax += round(t.amount, 2)

            if v23_val > 0:
                faktura.appendChild(self.create_element(doc, 'P_13_1', str(v23_val) ))
                faktura.appendChild(self.create_element(doc, 'P_14_1', str(v23_tax) ))
            if v8_val > 0:
                faktura.appendChild(self.create_element(doc, 'P_13_2', str(v8_val) ))
                faktura.appendChild(self.create_element(doc, 'P_14_2', str(v8_tax) ))
            if v5_val > 0:
                faktura.appendChild(self.create_element(doc, 'P_13_3', str(v5_val) ))
                faktura.appendChild(self.create_element(doc, 'P_14_3', str(v5_tax) ))
            if vunknown_val > 0:
                faktura.appendChild(self.create_element(doc, 'P_13_4', str(vunknown_val) ))
                faktura.appendChild(self.create_element(doc, 'P_14_4', str(vunknown_tax) ))
            if v0_val > 0:
                faktura.appendChild(self.create_element(doc, 'P_13_6', str(v0_val) ))
            if vz_val > 0:
                faktura.appendChild(self.create_element(doc, 'P_13_7', str(vz_val) ))

            faktura.appendChild(self.create_element(doc, 'P_15', str(round(i.amount_total, 2)) ))
            faktura.appendChild(self.create_element(doc, 'P_16', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_17', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_18', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_19', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_20', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_21', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_23', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_106E_2', 'false' ))
            faktura.appendChild(self.create_element(doc, 'P_106E_3', 'false' ))
            if i.type == 'out_invoice':
                faktura.appendChild(self.create_element(doc, 'RodzajFaktury', 'VAT'))
            elif i.type == 'out_refund':
                faktura.appendChild(self.create_element(doc, 'RodzajFaktury', 'KOREKTA'))
                faktura.appendChild(self.create_element(doc, 'PrzyczynaKorekty', i.name))
                faktura.appendChild(self.create_element(doc, 'NrFaKorygowanej', i.origin))
                faktura.appendChild(self.create_element(doc, 'OkresFaKorygowanej', i.date_invoice))

            jpk.appendChild(faktura)

        # FakturaCtrl
        if len(invoices) > 0:
            fakturaCtrl = doc.createElement('FakturaCtrl')
            fakturaCtrl.appendChild(self.create_element(doc, 'LiczbaFaktur', len(invoices)))
            fakturaCtrl.appendChild(self.create_element(doc, 'WartoscFaktur', str(round(invoicesTotalValue, 2))))
            jpk.appendChild(fakturaCtrl)

        # StawkiPodatku
        stawkiPodatku = doc.createElement('StawkiPodatku')
        stawkiPodatku.appendChild(self.create_element(doc, 'Stawka1', '0.23'))
        stawkiPodatku.appendChild(self.create_element(doc, 'Stawka2', '0.08'))
        stawkiPodatku.appendChild(self.create_element(doc, 'Stawka3', '0.05'))
        stawkiPodatku.appendChild(self.create_element(doc, 'Stawka4', '0.00'))
        stawkiPodatku.appendChild(self.create_element(doc, 'Stawka5', '0.00'))

        jpk.appendChild(stawkiPodatku)

        # FakturaWiersz - collection
        linesCount = 0
        linesValue = 0
        for i in invoices:
            linesCount += len(i.invoice_line_ids)
            for l in i.invoice_line_ids:
                linesValue += l.price_total
                fakturaWiersz = doc.createElement('FakturaWiersz')
                fakturaWiersz.setAttribute("typ", "G")
                fakturaWiersz.appendChild(self.create_element(doc, 'P_2B', i.number))
                fakturaWiersz.appendChild(self.create_element(doc, 'P_7', l.name))
                fakturaWiersz.appendChild(self.create_element(doc, 'P_8A', 'szt.'))
                fakturaWiersz.appendChild(self.create_element(doc, 'P_8B', str(round(l.quantity, 2))))
                fakturaWiersz.appendChild(self.create_element(doc, 'P_9A', str(round(l.price_unit, 2))))
                fakturaWiersz.appendChild(self.create_element(doc, 'P_11', str(round(l.price_subtotal, 2))))
                fakturaWiersz.appendChild(self.create_element(doc, 'P_11A', str(round(l.price_total, 2))))
                for t in l.invoice_line_tax_ids:
                    fakturaWiersz.appendChild(self.create_element(doc, 'P_12', str(round(t.amount)) ))
                jpk.appendChild(fakturaWiersz)

        # FakturaWierszCtrl
        if len(invoices) > 0:
            fakturaWierszCtrl = doc.createElement('FakturaWierszCtrl')
            fakturaWierszCtrl.appendChild(self.create_element(doc, 'LiczbaWierszyFaktur', linesCount))
            fakturaWierszCtrl.appendChild(self.create_element(doc, 'WartoscWierszyFaktur', str(round(linesValue, 2)) ))
            jpk.appendChild(fakturaWierszCtrl)

        doc.appendChild(jpk)

        file_data = doc.toprettyxml()

        values = {
            'name': "JPK_FA.xml",
            'datas_fname': 'JPK_FA.xml',
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas':  base64.encodestring(file_data.encode('utf-8')),
        }
        attachment_id = self.env['ir.attachment'].sudo().create(values)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
        }

    def create_element(self, root, name, val=''):
        elem = root.createElement(str(name))
        elem.appendChild(root.createTextNode(str(val)))

        return elem
