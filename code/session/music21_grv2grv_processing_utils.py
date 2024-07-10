import music21 as m21
from pathlib import Path
import pandas as pd
from typing import List, Dict, Tuple, Optional

# TODO: gev2grv flow - what is missing?:
# filter if in xlsx + midi exist (names eventualy taken from Tamir's excel) 
# auto-map midi and return dictionaries (what happens with channel 10 and midi program?)
# crop midi and save parts

# Run groove2groove
# map channels back
# drop generated drums and copy original drums


VALID_STRUCTURE_PART_NAMES = ['Verse', 'Verse 1', 'Verse 2', 'Verse 3', 'Verse 4', 'Verse 5',
                    'Pre - Chorus', 'Pre - Chorus 1', 'Pre - Chorus 2', 'Pre - Chorus 3', 'Pre - Chorus 4',  'Pre - Chorus 5',
                    'Chorus', 'Chorus 1', 'Chorus 2', 'Chorus 3', 'Chorus 4', 'Chorus 5', 
                    'Post - Chorus', 'Post - Chorus 1', 'Post - Chorus 2', 'Post - Chorus 3', 'Post - Chorus 4', 'Post - Chorus 5', 
                    'Intro', 'Interlude', 'C - Part', 'Coda', 'Outro', ]


def is_m21_part_drum(part: m21.stream.Part, part_name_drum_hints: List[str] = ['fx', 'drum', 'percussion']) -> bool:
    """
    Util function for understanding if a Part object contains drums.

    :param part: music21 Part object to be examined.
    :param part_name_drum_hints: list of strings that might appear in the part name for drums.
    :return: boolean, whether the part contains drum or not.
    """
    
    part_name = part.partName
    instr = part.getInstrument()
    
    # check parts that are mapped by default to channel 10
    default_prog_ch_dict,_ = m21.midi.translate.channelInstrumentData(part)
    if 10 in default_prog_ch_dict.values():
        return True

    # check part name and itterate over the part name hints for drums.
    elif part_name:
        for part_name_drum_hint in part_name_drum_hints:
            if part_name_drum_hint.lower() in part_name.lower():
                return True
        
        # check if part name is 'program##' or 'program##d' (as in grv2grv output) 
        if part_name.startswith('program'):
            if part_name.endswith('d'):
                return True
            # 113-120 are Percussive instruments. example: program114 --> percussion!
            if part_name[7:].isdigit() and (int(part_name[7:])>= 113) and (int(part_name[7:])<=120):
                return True

    # check by instrument
    elif instr:
        if isinstance(instr, (m21.instrument.Percussion, m21.instrument.UnpitchedPercussion)):
            return True
        if instr.midiChannel == 9:
            return True
        if instr.midiProgram is not None and (instr.midiProgram >= 113) and (instr.midiProgram <=120):
            return True
    else:    
        return False


def drop_drums(midi_stream: m21.stream.Score) -> m21.stream.Score:
    """Util function for INPLACE remooing drums from Score object.
    :param midi_stream: music21 Score object.
    :return: the modified midi stream without drums.
    """
    for part in midi_stream:
        if isinstance(part, m21.stream.Part):
            if is_m21_part_drum(part):
                midi_stream.remove(part)
    return midi_stream



def split_drum_from_midi_stream(midi_stream: m21.stream.Score
                                ) -> Tuple[m21.stream.Score,m21.stream.Score]:
    """Util function for INPLACE removing drums from Score object.
    :param midi_stream: music21 Score object.
    :return: two midi streams containing the instruments w/o drums, and the drums only.
    """
    midi_stream_no_drum= m21.stream.Score()
    midi_stream_drum_only= m21.stream.Score()

    for part in midi_stream:
        if isinstance(part, m21.metadata.Metadata):
            midi_stream_drum_only.append(part)
            midi_stream_no_drum.append(part)
        if isinstance(part, m21.stream.Part):
            if is_m21_part_drum(part):
                midi_stream_drum_only.append(part)
            else:
                midi_stream_no_drum.append(part)
    return midi_stream_no_drum, midi_stream_drum_only


def get_bpm_from_midi_stream(midi_stream: m21.stream.Score) -> Optional[float]:
    """Util for extracting the bpm from a midi stream.
    :param midi_stream: music21 Score object.
    :return: bpm as float if bpm can be extracted
    """
    metronome_marks = midi_stream.recurse().getElementsByClass(m21.tempo.MetronomeMark)
    if metronome_marks and len(metronome_marks) > 0:
        bpm = metronome_marks[0].number
        return bpm
    else:
        return None


def assign_bpm_to_midi_stream(midi_stream: m21.stream.Score, bpm: float) -> m21.stream.Score:
    """Util for asigning bpm to all parts of a midi stream.
    :param midi_stream: music21 Score object.
    :param bpm: requested BPM as float
    :return: modified midi_stream
    """
    for part in midi_stream:
        if isinstance(part, m21.metadata.Metadata):
            pass
        elif isinstance(part, m21.stream.Part):
            # check for existing metronome marks and replace their BPM:
            current_metronome_marks = part.flatten().getElementsByClass(m21.tempo.MetronomeMark)
            if current_metronome_marks is not None and len(current_metronome_marks) > 0:
                for current_metronome_mark in current_metronome_marks:
                    current_metronome_mark.number = bpm
            else:
                part.insert(0, m21.tempo.MetronomeMark(number=bpm))
    return midi_stream


def assign_program_to_midi_stream(midi_stream: m21.stream.Score, 
                                  remove_drums: bool = False) -> Tuple[m21.stream.Score, dict, dict]:
    """Util function for INPLACE assigning running midi program numbers to midi score.
    :param midi_stream: music21 Score object to mapped.
    :param remove_drums: boolean, parameter for removing drums
    :return: modified midi_stream, program dictionary (for harmonic instruments), drum dictionary (for percussion)
    """
    program_dict = {}
    drum_dict = {}

    running_prog_num = 1
    for part in midi_stream:
        if isinstance(part, m21.metadata.Metadata):
            pass
        elif isinstance(part, m21.stream.Part):
            part_name = part.partName 
            if is_m21_part_drum(part):
                # drums
                if remove_drums:
                    midi_stream.remove(part)
                else:
                    running_prog_num+=1
                    drum_dict[running_prog_num] = part_name
                    # TODO what about program numbers 113-120? shoud stay the same instrument and not Unpitched Percussion
                    instrument = m21.instrument.UnpitchedPercussion()
                    # Check this:
                    # instrument.midiProgram = running_prog_num
            else:
                # pitched instrument
                running_prog_num+=1
                program_dict[running_prog_num] = part_name
                instrument = m21.instrument.instrumentFromMidiProgram(running_prog_num)

            instrument.partName = part.partName
            part[0].replace(part[0].flatten().getInstrument(), instrument)
    return midi_stream, program_dict, drum_dict


def crop_midi_stream_by_bars(midi_stream: m21.stream.Score, 
                             first_bar:int, 
                             last_bar:int,
                             ) -> m21.stream.Score:
    """Crop Midi Score by bars, assuming all parts start at measure=0 and offset=0.
    Not sure that handles also different Keys.
    Assuming only a single BPM for the entire stream.

    :param midi_stream: music21 Score object to be cropped.
    :param first_bar: first bar (inclusive)
    :param last_bar: last bar number (inclusive)
    :part_name: str to be used in the metadata
    :title: str to be used in the metadata
    :return: new music21 Score object containing only the relevant bars
    """
    
    cropped_score = m21.stream.Score()

    # assuming only one BPM:
    bpm = get_bpm_from_midi_stream(midi_stream)

    for part in midi_stream:
        if isinstance(part, m21.metadata.Metadata):
            cropped_score.append(part)
        elif isinstance(part, m21.stream.Part):
            measures = part.measures(first_bar, last_bar)
            # keep only measures with finite length
            if len(measures):
                if bpm:
                    measures.insert(0, m21.tempo.MetronomeMark(number=bpm))
                cropped_score.append(measures)
        else: 
            print(f'part {part} of unknown type {type(part)}')

    return cropped_score            
            

def preprocess_midi_file(midi_path,
                         part_struct_first_and_last_bar_dict: Dict[str, Tuple[int, int]] = {}, 
                         auto_map_midi = True,
                         split_drum = True,
                         ) -> Tuple[Dict[str, m21.stream.Score], Dict[int, str], Dict[int, str], float]:
    """
    :param midi_path: path to midi score
    :part_struct_first_and_last_bar_dict: dict of the following form: {structure_part_name: (first_bar, last_bar)}. 
                                          first and last bar are ints indicating the first and last bars for cropping.
    :param auto_map_midi: bool flag for enabling sequential midi program number mapping (used to overcome plug-in problems for midi files without program mapping) 
    :param split_drum: bool flag for splitting the drums to different scores.
    :return: tuple of (stream_dict, program_dict, drum_dict, bpm). the first is a dictionary containing the processed music21 streams, the others are mapping dictionaries and bpm.
    """
    program_dict, drum_dict = {}, {}
    stream_dict = {}

    midi_stream = m21.converter.parse(midi_path)
    bpm = get_bpm_from_midi_stream(midi_stream)
    # auto mapping if required:
    if auto_map_midi:
        midi_stream, program_dict, drum_dict = assign_program_to_midi_stream(midi_stream, remove_drums=False)

    # crop:
    if part_struct_first_and_last_bar_dict:
        for struct_part in part_struct_first_and_last_bar_dict.keys():
            first_bar, last_bar = part_struct_first_and_last_bar_dict[struct_part]

            midi_stream_cropped = crop_midi_stream_by_bars(midi_stream, first_bar, last_bar)

            if split_drum:
                midi_stream_cropped_no_drum, midi_stream_cropped_only_drum = split_drum_from_midi_stream(midi_stream_cropped)
                stream_dict[struct_part + '_no_drum'] = midi_stream_cropped_no_drum
                stream_dict[struct_part + '_only_drum'] = midi_stream_cropped_only_drum
            else:
                stream_dict[struct_part] = midi_stream_cropped
    else:
        if split_drum:
            midi_stream_cropped_no_drum, midi_stream_cropped_only_drum = split_drum_from_midi_stream(midi_stream)
            stream_dict['full_no_drum'] = midi_stream_cropped_no_drum
            stream_dict['full_only_drum'] = midi_stream_cropped_only_drum
        else:
            stream_dict['full'] = midi_stream  # shouldn't I take full length as a default?

    return stream_dict, program_dict, drum_dict, bpm



def get_stucture_dict_from_xls(structure_xls_path, 
                               structure_part_names: List[str] = [],
                               fix_part_names=True, 
                               remove_last_char_1_in_part_name=True,
                               ) -> Dict[str, Tuple[int, int]]:
    """util function for extracting a dictionary of structure part names and the start_bar, end_bar 
    from session structure xls.
    :param structure_xls_path: path to the structure xls
    :param structure_part_names: list of str - of specific structure parts required (otherwise takes all)
    :param fix_part_names: bool, to fix the part names to Title case without spaces and dashes.
    :param remove_last_char_1_in_part_name: remove the figure '1' from the end of a part name: example Verse1->Verse
    :return: dictionary with sturcute_part_name as key and (start_bar, end_bar) as value.
    """
        
    if not Path(structure_xls_path).exists():
        print(f'input_structure_xls {structure_xls_path} does not exist')
        return {}

    df_structure = pd.read_excel(structure_xls_path)
    
    for col in ['Part','Startbar','Endbar']:
        if col not in df_structure.columns:
            print(f"column '{col}' not in '{structure_xls_path}'. only {df_structure.columns}")
            return
    df_structure = df_structure[['Part','Startbar','Endbar']].dropna(how='all')

    # remove spaces from part names
    if fix_part_names:
        df_structure['Part_fixed_name'] = df_structure['Part'].str.title().str.replace(' ','').str.replace('-','')
    else:
        df_structure['Part_fixed_name'] = df_structure['Part']
    if remove_last_char_1_in_part_name:
        df_structure['Part_fixed_name'] = df_structure['Part_fixed_name'].apply(lambda x: x[:-1] if x.endswith('1') else x)

    # get dict using the 'Part' name w/o spaces as key and the ('Startbar','Endbar') as values.
    all_struct_first_and_last_bar_dict = df_structure.set_index('Part_fixed_name')[['Startbar', 'Endbar']].astype(int).apply(tuple, axis=1).to_dict()

    if not structure_part_names:
        return all_struct_first_and_last_bar_dict
    
    else:
        partial_struct_first_and_last_bar_dict = {}
        for structure_part_name in structure_part_names:
            name_fixed = structure_part_name.title().replace(' ','').replace('-','') if fix_part_names else structure_part_name

            if name_fixed in all_struct_first_and_last_bar_dict: 
                partial_struct_first_and_last_bar_dict[name_fixed] = all_struct_first_and_last_bar_dict[name_fixed]
            else:
                print(f"Part '{structure_part_name}' not found in '{structure_xls_path}', only: {df_structure['Part'].values}")

        return partial_struct_first_and_last_bar_dict



def find_structure_invalid_names_in_xls(structure_xls_path, 
                                        valid_structure_part_names: List[str] = VALID_STRUCTURE_PART_NAMES,
                                        fix_part_names=False, 
                                        strip_part_names=False, 
                                        verbose=True) -> List[str]:
    """
    :param structure_xls_path: path to the structure xls
    :param valid_structure_part_names: list of str - valid part names
    :param fix_part_names: bool, to fix the part names to Title case without spaces and dashes.
    :param strip_part_names: bool, to strip the part names from spaces at the beginning and end.
    :param verbose: bool, print validation status.
    :return: list of invalid parts.
    """
        
    if not Path(structure_xls_path).exists():
        if verbose:
            print(f'input_structure_xls {structure_xls_path} does not exist')
        return []

    df_structure = pd.read_excel(structure_xls_path)
    
    for col in ['Part','Startbar','Endbar']:
        if col not in df_structure.columns:
            if verbose:
                print(f"column '{col}' not in '{structure_xls_path}'. only {df_structure.columns}")
            return []

    # get rid of NaN rows
    df_structure = df_structure.dropna(how='all', subset=['Part','Startbar','Endbar'])


    # remove spaces from part names
    if fix_part_names:
        df_structure['Part_fixed_name'] = df_structure['Part'].str.title().str.replace(' ','').str.replace('-','')
    elif strip_part_names:
        df_structure['Part_fixed_name'] = df_structure['Part'].str.strip()
    else:
        df_structure['Part_fixed_name'] = df_structure['Part']

    all_struct_first_and_last_bar_dict = df_structure.set_index('Part_fixed_name')[['Startbar', 'Endbar']].astype(int).apply(tuple, axis=1).to_dict()

    if fix_part_names:
        valid_structure_part_names = [p.title().replace(' ','').replace('-','') for p in valid_structure_part_names] 
    
    invalid_part_names = [p for p in all_struct_first_and_last_bar_dict.keys() if p not in valid_structure_part_names]

    
    if invalid_part_names:
        invalid_part_names_str = "'" + "', '".join(invalid_part_names) + "'"
        if verbose:
            print(f"{Path(structure_xls_path).name}\tinvalid: {invalid_part_names_str}")
    return invalid_part_names



def assign_part_name_to_grv2grv_output_midi_stream_by_program_dict(
        midi_stream: m21.stream.Score, 
        program_dict: Dict[str, m21.stream.Score],
        remove_drum: bool=True) -> m21.stream.Score:
    """Util function for assigning music21 Score object part-names instead 
        of program numbers for reversing midi-mapping.
        Used for groove2groove outputs where there are no program numbers and 
        part-names are 'program##' or 'program##d' for drums.
    :param midi_stream: music21 Score object to be modified
    :param program_dict: dictionary with mapping between program names (int) and the original part name
    :param remove_drums: bool, flag for removing drums.
    :return: modified music21 Score object
    """
    
    for part in midi_stream:
        if isinstance(part, m21.metadata.Metadata):
            pass
        elif isinstance(part, m21.stream.Part):
            part_name = part.partName 
            if part_name and part_name.startswith('program'):
                if part_name[-1] == 'd':
                    if remove_drum:
                    # drums - do not include the part # TODO - check it out
                        print(f"removing part: '{part_name}'")
                        midi_stream.remove(part)
                        # also - what about programs with the numbers 113-120?
                        continue
                    else:
                        prog_str = part_name[7:-1] # remove 'program' and 'd' from the name program##d
                        instrument_mapped_name = program_dict.get(prog_str,f'{part_name} (percussion not in dict)')
                        part.partName = instrument_mapped_name
                        new_instrument = m21.instrument.UnpitchedPercussion()
                else:
                    prog_str = part_name[7:]
                    instrument_mapped_name = program_dict.get(prog_str,f'{part_name} (not in dict)')
                    part.partName = instrument_mapped_name
                    new_instrument = m21.instrument.Instrument()
                    #new_instrument = m21.instrument.Instrument(instrument_mapped_name)
                new_instrument.partName = instrument_mapped_name
                part[0].replace(part[0].flatten().getInstrument(), new_instrument)
    return midi_stream



def replace_drums_in_midi_stream(midi_stream: m21.stream.Score, 
                                 drum_midi_stream: m21.stream.Score,
                                 fix_multiple_instruments_in_a_part: bool=True,
                                 ) -> m21.stream.Score:
    """Util function for combining the non-drum parts of a first stream with the drum-parts of another. 
    :param midi_stream: midi stream to copy all parts excluding drums
    :param drum_midi_stream: midi stream to copy only drums
    :param fix_multiple_instrument_in_single_part: boolean flag for removing excessive instruments
         in case more than one instruments are assigned to a part. this is for fixing a problem with plugins.
    :return: new Score object containing the non-drum parts of the first midi and the drum parts of the second midi.
    """ 
    new_midi = m21.stream.Score()

    for part in midi_stream:
        # copy metadata from the pitched part
        if isinstance(part, m21.metadata.Metadata):
            new_midi.append(part)
        elif isinstance(part, m21.stream.Part):
            if not is_m21_part_drum(part):
                if fix_multiple_instruments_in_a_part:
                    # check if there are multiple instrument classes in the part
                    instruments = part.flat.getElementsByClass(m21.instrument.Instrument)
                    if len(instruments) > 1:
                        # keep only the last instrument and asign the partName as the instrument name
                        instruments[-1].instrumentName = part.partName
                        for instrument in instruments[:-1]:
                            part[0].remove(instrument)
                new_midi.append(part)
                
    for part in drum_midi_stream:
        if isinstance(part, m21.metadata.Metadata):
            pass
        elif isinstance(part, m21.stream.Part):
            if is_m21_part_drum(part):
                if fix_multiple_instruments_in_a_part:
                    # check if there are multiple instrument classes in the part
                    instruments = part.flat.getElementsByClass(m21.instrument.Instrument)
                    if len(instruments) > 1:
                        # keep only the last instrument and asign the partName as the instrument name
                        instruments[-1].instrumentName = part.partName
                        for instrument in instruments[:-1]:
                            part[0].remove(instrument)
                new_midi.append(part)
    return new_midi