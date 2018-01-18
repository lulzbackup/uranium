// Copyright (c) 2015 Ultimaker B.V.
// Uranium is released under the terms of the AGPLv3 or higher.

import QtQuick 2.2
import QtQuick.Controls 1.2

import UM 1.1 as UM

Item
{
    id: base
    width: childrenRect.width
    height: childrenRect.height
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
        var input= parseInt(input)
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
            color: UM.Theme.getColor("x_axis");
            verticalAlignment: Text.AlignVCenter;
        }

        Label
        {
            height: UM.Theme.getSize("setting_control").height;
            text: "Y";
            font: UM.Theme.getFont("default");
            color: UM.Theme.getColor("z_axis"); // This is intentional. The internal axis are switched.
            verticalAlignment: Text.AlignVCenter;
        }

        Label
        {
            height: UM.Theme.getSize("setting_control").height;
            text: "Z";
            font: UM.Theme.getFont("default");
            color: UM.Theme.getColor("y_axis"); // This is intentional. The internal axis are switched.
            verticalAlignment: Text.AlignVCenter;
        }
        TextField
        {
            id: xTextField
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            property string unit: "degrees";
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
            id: yTextField
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            property string unit: "degrees";
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
        TextField
        {
            id: zTextField
            width: UM.Theme.getSize("setting_control").width;
            height: UM.Theme.getSize("setting_control").height;
            property string unit: "degrees";
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
    }

    Button
    {
        id: resetRotationButton

        anchors.left: parent.left;
        anchors.top: textfields.bottom;
        anchors.topMargin: UM.Theme.getSize("default_margin").width;
        anchors.leftMargin: UM.Theme.getSize("default_margin").width;


        //: Reset Rotation tool button
        text: catalog.i18nc("@action:button","Reset")
        iconSource: UM.Theme.getIcon("rotate_reset");

        style: UM.Theme.styles.tool_button;
        z: 1

        onClicked:
        {
            base.xText = "0"
            base.yText = "0"
            base.zText = "0"
            UM.ActiveTool.triggerAction("resetRotation");
        }
    }

    Button
    {
        id: layFlatButton

        anchors.left: resetRotationButton.right;
        anchors.top: textfields.bottom;
        anchors.leftMargin: UM.Theme.getSize("default_margin").width;
        anchors.topMargin: UM.Theme.getSize("default_margin").width;

        //: Lay Flat tool button
        text: catalog.i18nc("@action:button","Lay flat")
        iconSource: UM.Theme.getIcon("rotate_layflat");

        style: UM.Theme.styles.tool_button;

        onClicked: UM.ActiveTool.triggerAction("layFlat");
    }

    CheckBox
    {
        anchors.left: parent.left;
        anchors.top: resetRotationButton.bottom;
        anchors.topMargin: UM.Theme.getSize("default_margin").width;

        //: Snap Rotation checkbox
        text: catalog.i18nc("@action:checkbox","Snap Rotation");

        style: UM.Theme.styles.checkbox;

        checked: UM.ActiveTool.properties.getValue("RotationSnap");
        onClicked: UM.ActiveTool.setProperty("RotationSnap", checked);
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
        value: base.roundFloat(UM.ActiveTool.properties.getValue("Z"), 4)
    }

}
