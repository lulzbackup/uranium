// Copyright (c) 2016 Ultimaker B.V.
// Uranium is released under the terms of the AGPLv3 or higher.

import QtQuick 2.2
import QtQuick.Controls 1.2

import UM 1.1 as UM

Item
{
    id: base
    width: Math.max(14 * UM.Theme.getSize("line").width, childrenRect.width);
    height: Math.max(4.5 * UM.Theme.getSize("line").height, childrenRect.height);
    UM.I18nCatalog { id: catalog; name:"uranium"}

    property string xText
    property string yText
    property string zText

    //Rounds a floating point number to 4 decimals. This prevents floating
    //point rounding errors.
    //
    //input:    The number to round.
    //decimals: The number of decimals (digits after the radix) to round to.
    //return:   The rounded number.
    function roundFloat(input, decimals)
    {
        //First convert to fixed-point notation to round the number to 4 decimals and not introduce new floating point errors.
        //Then convert to a string (is implicit). The fixed-point notation will be something like "3.200".
        //Then remove any trailing zeroes and the radix.
        var output = input.toFixed(decimals).replace(/\.?0*$/, ""); //Match on periods, if any ( \.? ), followed by any number of zeros ( 0* ), then the end of string ( $ ).
        if(output == "-0")
        {
            output = "0";
        }
        return output;
    }

    function inc_dec(prop, event)
    {
        if (event.key == Qt.Key_Up) {
            var t = parseFloat(UM.ActiveTool.properties.getValue(prop)) + 1.0;
            UM.ActiveTool.setProperty(prop, t);
            event.accepted = true;
        }
        if (event.key == Qt.Key_Down) {
            var t = parseFloat(UM.ActiveTool.properties.getValue(prop)) - 1.0;
            UM.ActiveTool.setProperty(prop, t);
            event.accepted = true;
        }
    }

    Button
    {
        id: resetPositionButton

        //: Reset position tool button
        text: catalog.i18nc("@action:button","Center on Build Plate")
        iconSource: UM.Theme.getIcon("scale_reset");

        anchors.top: dropToBuildplateButton.bottom;
        anchors.topMargin: UM.Theme.getSize("default_margin").height;
        z: 1

        style: UM.Theme.styles.tool_button;

        onClicked: UM.ActiveTool.triggerAction("resetPosition");
        visible: false
    }

    Button
    {
        id: dropToBuildplateButton

        //: Drop to build plate tool button
        text: catalog.i18nc("@action:button","Drop to Build Plate");
        iconSource: UM.Theme.getIcon("scale_reset");

        anchors.top: parent.top;
        z: 1

        style: UM.Theme.styles.tool_button;
        onClicked: UM.ActiveTool.triggerAction("dropToBuildplate")
        visible: false
    }

    Grid
    {
        id: textfields;

        anchors.leftMargin: UM.Theme.getSize("default_margin").width;
        anchors.top: parent.top;

        columns: 2;
        flow: Grid.TopToBottom;
        spacing: UM.Theme.getSize("default_margin").width / 2;

        Label
        {
            height: UM.Theme.getSize("setting_control").height;
            text: "X";
            font: UM.Theme.getFont("default");
            color: "red"
            verticalAlignment: Text.AlignVCenter;
        }

        Label
        {
            height: UM.Theme.getSize("setting_control").height;
            text: "Y";
            font: UM.Theme.getFont("default");
            color: "green"
            verticalAlignment: Text.AlignVCenter;
        }

        Label
        {
            height: UM.Theme.getSize("setting_control").height;
            text: "Z";
            font: UM.Theme.getFont("default");
            color: "blue"
            verticalAlignment: Text.AlignVCenter;
        }
        TextField
        {
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            property string unit: "mm";
            style: UM.Theme.styles.text_field;
            text: xText
            validator: DoubleValidator
            {
                decimals: 4
                locale: "en_US"
            }

            onEditingFinished:
            {
                var modified_text = text.replace(",", ".") // User convenience. We use dots for decimal values
                UM.ActiveTool.setProperty("X", modified_text);
            }

            Keys.onPressed:
            {
                base.inc_dec("X", event);
            }
        }
        TextField
        {
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            property string unit: "mm";
            style: UM.Theme.styles.text_field;
            text: yText
            validator: DoubleValidator
            {
                decimals: 4
                locale: "en_US"
            }

            onEditingFinished:
            {
                var modified_text = text.replace(",", ".") // User convenience. We use dots for decimal values
                UM.ActiveTool.setProperty("Y", modified_text);
            }

            Keys.onPressed:
            {
                base.inc_dec("Y", event);
            }
        }
        TextField
        {
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            property string unit: "mm";
            style: UM.Theme.styles.text_field;
            text: zText
            validator: DoubleValidator
            {
                decimals: 4
                locale: "en_US"
            }

            onEditingFinished:
            {
                var modified_text = text.replace(",", ".") // User convenience. We use dots for decimal values
                UM.ActiveTool.setProperty("Z", modified_text);
            }

            Keys.onPressed:
            {
                base.inc_dec("Z", event);
            }
        }
    }

    // We have to use indirect bindings, as the values can be changed from the outside, which could cause breaks
    // (for instance, a value would be set, but it would be impossible to change it).
    // Doing it indirectly does not break these.
    Binding
    {
        target: base
        property: "xText"
        value: base.roundFloat(UM.ActiveTool.properties.getValue("X"), 4)
    }

    Binding
    {
        target: base
        property: "yText"
        value: base.roundFloat(UM.ActiveTool.properties.getValue("Y"), 4)
    }

    Binding
    {
        target: base
        property: "zText"
        value:base.roundFloat(UM.ActiveTool.properties.getValue("Z"), 4)
    }
}