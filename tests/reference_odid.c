/* Generate synthetic decoder fixtures with the OpenDroneID reference encoder.
 * Compile against libopendroneid (Apache-2.0), never transmit these messages.
 * See docs/DETECTION.md for provenance and the reproduction command.
 */
#include "opendroneid.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static void output(const char *name, const void *value, int status) {
    if(status != ODID_SUCCESS) exit(2);
    const unsigned char *bytes=value;
    printf("%s ",name);
    for(int i=0;i<25;i++) printf("%02x",bytes[i]);
    puts("");
}
int main(void) {
    ODID_BasicID_data b; ODID_BasicID_encoded be;
    odid_initBasicIDData(&b); b.IDType=1; b.UAType=2; strcpy(b.UASID,"QM-SYNTHETIC-001");
    int status=encodeBasicIDMessage(&be,&b); output("basic",&be,status);
    ODID_Location_data l; ODID_Location_encoded le;
    odid_initLocationData(&l); l.Status=2; l.Direction=270; l.SpeedHorizontal=70.5f;
    l.SpeedVertical=-2; l.Latitude=1.25; l.Longitude=-2.5; l.AltitudeBaro=100;
    l.AltitudeGeo=120.5f; l.HeightType=1; l.Height=50; l.TimeStamp=123.4f;
    status=encodeLocationMessage(&le,&l); output("location",&le,status);
    odid_initLocationData(&l); l.TimeStamp=65535; status=encodeLocationMessage(&le,&l); output("unknown",&le,status);
    ODID_Auth_data a; ODID_Auth_encoded ae;
    odid_initAuthData(&a); a.AuthType=1; a.DataPage=0; a.LastPageIndex=1; a.Length=20;
    a.Timestamp=100; memset(a.AuthData,0x5a,17);
    status=encodeAuthMessage(&ae,&a); output("auth",&ae,status);
    ODID_SelfID_data s; ODID_SelfID_encoded se;
    odid_initSelfIDData(&s); strcpy(s.Desc,"SYNTHETIC TEST ONLY");
    status=encodeSelfIDMessage(&se,&s); output("self",&se,status);
    ODID_System_data y; ODID_System_encoded ye;
    odid_initSystemData(&y); y.OperatorLatitude=1.5; y.OperatorLongitude=-2.75;
    y.OperatorLocationType=1; y.ClassificationType=1; y.AreaCount=2; y.AreaRadius=30;
    y.AreaCeiling=200; y.AreaFloor=10; y.CategoryEU=1; y.ClassEU=2;
    y.OperatorAltitudeGeo=12; y.Timestamp=123456;
    status=encodeSystemMessage(&ye,&y); output("system",&ye,status);
    ODID_OperatorID_data o; ODID_OperatorID_encoded oe;
    odid_initOperatorIDData(&o); strcpy(o.OperatorId,"QM-TEST-OPERATOR");
    status=encodeOperatorIDMessage(&oe,&o); output("operator",&oe,status);
    return 0;
}
