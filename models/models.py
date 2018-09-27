# -*- coding: utf-8 -*-

import base64
import datetime
import pytz
import xml.dom.minidom
from odoo import models, fields, api

class ideas_jpk_fa(models.TransientModel):
    _name = 'ideas_jpk_fa.generator'

    dateStart = fields.Date(default=fields.Date.today(), required=True)
    dateEnd = fields.Date(default=fields.Date.today(), required=True)
    company = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, required=True)
    currency = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, domain="[('active', '=', 'TRUE')]", required=True)
    purpose = fields.Selection([
            ('1', 'złożenie'),
            ('2', 'korekta'),
    ], default="1", required=True)
    uscode = fields.Char(required=True)

    @api.multi
    def generate_file(self):
        local_tz = pytz.timezone(self.env.user.tz or 'UTC')

        invoices = self.env['account.invoice'].search([
                        ('date_invoice', '>=', self.dateStart),
                        ('date_invoice', '<=', self.dateEnd),
                        ('company_id', '=', self.company.id),
                        ('currency_id', '=', self.currency.id),
                        ('type', '=', 'out_invoice'),
                        ('state', 'in', ('paid', 'open',))
        ])
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

        wariantFormularza = doc.createElement('WariantFormularza')
        wariantFormularza.appendChild(doc.createTextNode("1"))
        naglowek.appendChild(wariantFormularza)

        celZlozenia = doc.createElement('CelZlozenia')
        celZlozenia.appendChild(doc.createTextNode(self.purpose))
        naglowek.appendChild(celZlozenia)

        dataWytworzeniaJPK = doc.createElement('DataWytworzeniaJPK')
        local_date = datetime.datetime.now().astimezone(local_tz).strftime('%Y-%m-%dT%H:%M')
        dataWytworzeniaJPK.appendChild(doc.createTextNode(local_date))
        naglowek.appendChild(dataWytworzeniaJPK)

        dataOd = doc.createElement('DataOd')
        dataOd.appendChild(doc.createTextNode(self.dateStart))
        naglowek.appendChild(dataOd)

        dataDo = doc.createElement('DataDo')
        dataDo.appendChild(doc.createTextNode(self.dateEnd))
        naglowek.appendChild(dataDo)

        domyslnyKodWaluty = doc.createElement('DomyslnyKodWaluty')
        domyslnyKodWaluty.appendChild(doc.createTextNode(self.currency.name))
        naglowek.appendChild(domyslnyKodWaluty)

        kodUrzedu = doc.createElement('KodUrzedu')
        kodUrzedu.appendChild(doc.createTextNode(self.uscode))
        naglowek.appendChild(kodUrzedu)

        jpk.appendChild(naglowek)

        # Podmiot1
        podmiot1 = doc.createElement('Podmiot1')

        etdNIP = doc.createElement('etd:NIP')
        etdNIP.appendChild(doc.createTextNode('NIP'))
        podmiot1.appendChild(etdNIP)

        jpk.appendChild(podmiot1)

        # Faktura - collection
        faktura = doc.createElement('Faktura')
        faktura.setAttribute("typ", "G")
        jpk.appendChild(faktura)

        # FakturaCtrl
        fakturaCtrl = doc.createElement('FakturaCtrl')
        jpk.appendChild(fakturaCtrl)

        # StawkiPodatku
        stawkiPodatku = doc.createElement('StawkiPodatku')
        jpk.appendChild(stawkiPodatku)

        # FakturaWiersz - collection
        fakturaWiersz = doc.createElement('FakturaWiersz')
        faktura.setAttribute("typ", "G")
        jpk.appendChild(fakturaWiersz)

        # FakturaWierszCtrl
        fakturaWierszCtrl = doc.createElement('FakturaWierszCtrl')
        jpk.appendChild(fakturaWierszCtrl)

        doc.appendChild(jpk)
        print(doc.toprettyxml())
        print(invoices)

        return doc.toprettyxml()
