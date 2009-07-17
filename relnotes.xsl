<xsl:stylesheet version="1.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="/">

        <html>
        <head>
            <title>Contexo Release Notes</title>
        </head>
        <body>
            <span style="font-size: 12pt; color: #336699; font-family: Verdana"><strong>
            CONTEXO RELEASE NOTES
            </strong></span><br />
                <span style="color: #cccccc; font-family: Verdana">
                --------------------------------------
                </span><br /><br />

                <xsl:for-each select="release_notes/release">
                    <span style="font-size: 12pt; font-family: Verdana; color: #cc6600">
                        <xsl:apply-templates select="title"/><br/>
                    </span>
                    <br />
                    <span style="color: #336699; font-family: Verdana; font-size: 8pt;"><strong>[COMMENTS]</strong></span>
                    <table cellpadding="4" style="font-family: Verdana" width="640">
                      <xsl:for-each select="comments">
                          <tr><td style="width: 439px">
                            <span style="font-size: 7pt"><xsl:apply-templates select="entry"/></span></td></tr>
                      </xsl:for-each>
                    </table>
                    <br />

                    <span style="color: #336699; font-family: Verdana; font-size: 8pt;"><strong>[CHANGES]</strong></span>
                      <xsl:for-each select="changes">
                      <br/><br/><span style="color: #334455; font-family: Verdana; font-size: 7pt;"><strong>Noteable changes/additions:</strong></span>
                        <table cellpadding="4" border="0" style="font-family: Verdana" width="640">
                          <xsl:for-each select="add">
                          
                             <xsl:variable name="haveNewlines"><xsl:value-of select="@multiline"/></xsl:variable>
                             <xsl:choose>

                               <xsl:when test="$haveNewlines = 1">
                               <!-- Multiple row output -->
                                 <tr><td width="5%" valign="top"><span style="font-size: 7pt">-</span></td>
                                 <td width="95%"><span style="font-size: 7pt">
                                  <xsl:for-each select="row">
                                    <xsl:apply-templates/><br/>
                                  </xsl:for-each>
                                 </span></td></tr>                               
                               </xsl:when>

                               <xsl:otherwise>
                               <!-- Single row output -->
                                 <tr><td width="5%" valign="top"><span style="font-size: 7pt">-</span></td>
                                 <td width="95%"><span style="font-size: 7pt">
                                    <xsl:apply-templates/>
                                 </span></td></tr>                               
                               </xsl:otherwise>

                             </xsl:choose>
                          </xsl:for-each>
                        </table>
                        <br/>
                        <span style="color: #334455; font-family: Verdana; font-size: 7pt;"><strong>Modifications/adjustments:</strong></span>
                        <table cellpadding="4" border="0" style="font-family: Verdana" width="640">
                        <xsl:for-each select="mod">
                              <tr><td width="5%" valign="top"><span style="font-size: 7pt">-</span></td>
                                <td style="width: 439px"><span style="font-size: 7pt">
                                <xsl:apply-templates/>
                                </span></td></tr>
                          </xsl:for-each>
                        </table>
                        <br/>
                      <span style="color: #334455; font-family: Verdana; font-size: 7pt;"><strong>Bugfixes:</strong></span>
                        <table cellpadding="4" border="0" style="font-family: Verdana" width="640">
                          <xsl:for-each select="bugfix">
                              <tr><td width="5%" valign="top"><span style="font-size: 7pt">-</span></td>
                                  <td style="width: 439px"><span style="font-size: 7pt">
                                <xsl:apply-templates/>
                                </span></td></tr>
                          </xsl:for-each>
                        </table>
                      </xsl:for-each>
                    <br />

                    <span style="color: #336699; font-family: Verdana; font-size: 8pt;"><strong>[KNOWN ISSUES]</strong></span>
                      <xsl:for-each select="known_issues">
                        <table cellpadding="4" border="0" style="font-family: Verdana" width="640">
                        <xsl:for-each select="entry">
                              <tr><td width="5%" valign="top"><span style="font-size: 7pt">-</span></td>
                                <td style="width: 439px"><span style="font-size: 7pt">
                                <xsl:apply-templates/>
                                </span></td></tr>
                          </xsl:for-each>
                        </table>
                      </xsl:for-each>
                    <br />
                    <br />
                    <br />
                </xsl:for-each>

        </body>
        </html>
    </xsl:template>
</xsl:stylesheet>